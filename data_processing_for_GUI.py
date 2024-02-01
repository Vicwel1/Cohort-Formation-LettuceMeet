# This is the file that is called by the GUI to process the data and form the cohorts. You do not need to modify or run this file.

import json
from datetime import datetime, timedelta
from itertools import combinations


def extract_participant_availabilities(data, time_block, skip_list=[]):
    """Extract time availabilities for each applicant."""
    participants_availabilities = {}
    not_available = []

    # Construct list of possible time slots for the event
    possible_times = []
    pollStartTime = data['data']['event']['pollStartTime']
    pollEndTime = data['data']['event']['pollEndTime']
    pollDates = data['data']['event']['pollDates']

    for date in pollDates:
        possible_times.append((datetime.strptime(date + "T" + pollStartTime, "%Y-%m-%dT%H:%M:%S.%fZ"), datetime.strptime(date + "T" + pollEndTime, "%Y-%m-%dT%H:%M:%S.%fZ")))

    # Iterate through each response and extract time slots
    for response in data['data']['event']['pollResponses']:
        applicant_name = response['user']['name']
        if applicant_name in skip_list:
            print(f'Skipping {applicant_name}')
            continue

        # Convert availability times to datetime objects
        time_slots = [
            (
                datetime.strptime(availability['start'], "%Y-%m-%dT%H:%M:%S.%fZ"),
                datetime.strptime(availability['end'], "%Y-%m-%dT%H:%M:%S.%fZ")
            )
            for availability in response['availabilities']
        ]

        # Check if the participant is available for the required time block
        if not any(e-s >= timedelta(hours=time_block) for s, e in time_slots):
            not_available.append(applicant_name)
            continue

        participants_availabilities[applicant_name] = time_slots

    return participants_availabilities, possible_times, not_available


def extract_facilitator_availabilities(data, names=False):
    """Extract facilitator availabilities from the data"""

    facilitators_availabilities = {}
    facilitator_names = []
    # for date in data['data']['event']['pollDates']:


    # Iterate through each response and extract facilitator availabilities
    for response in data['data']['event']['pollResponses']:
        applicant_name = response['user']['name']
        time_slots = [
            (
                datetime.strptime(availability['start'], "%Y-%m-%dT%H:%M:%S.%fZ"),
                datetime.strptime(availability['end'], "%Y-%m-%dT%H:%M:%S.%fZ")
            )
            for availability in response['availabilities']
        ]
        facilitators_availabilities[applicant_name] = time_slots
        facilitator_names.append(applicant_name)

    # Return either names or availabilities based on the 'names' flag
    return facilitator_names if names else facilitators_availabilities


def find_all_possible_cohorts(participants_availabilities, facilitators_availabilities, min_cohort_size, max_cohort_size, time_block, possible_times):
    """Find all possible cohorts given participants and facilitators availabilities."""
    possible_cohorts = []

    # Iterate through each possible day and time slot
    for day in possible_times:
        start_time = day[0]
        end_time = day[1]
        current_time = start_time
        while current_time + timedelta(hours=time_block) <= end_time:
            slot_end_time = current_time + timedelta(hours=time_block)

            # Check facilitator availability for the time slot
            available_facilitators = [
                f for f in facilitators_availabilities
                if any(s <= current_time and e >= slot_end_time for s, e in facilitators_availabilities[f][0]) and facilitators_availabilities[f][1] > 0
            ]
            if not available_facilitators:
                current_time += timedelta(minutes=30)
                continue

            # Check participant availability for the time slot
            available_participants = [
                p for p in participants_availabilities
                if any(s <= current_time and e >= slot_end_time for s, e in participants_availabilities[p])
            ]

            # Generate all combinations of participants for the cohort
            for size in range(min_cohort_size, max_cohort_size + 1):
                for cohort in combinations(available_participants, size):
                    possible_cohorts.append((current_time, slot_end_time, cohort))

            
            current_time += timedelta(minutes=30)
    return possible_cohorts


def is_feasible(possible_cohorts, num_cohorts, min_size, facilitators_info):
    """Check if it's feasible to form the requested number of cohorts."""
    if len(possible_cohorts) < num_cohorts:
        return False

    total_capacity = sum(info[1] for info in facilitators_info.values())
    if total_capacity < num_cohorts:
        return False

    # Additional checks can be added here based on other constraints

    return True


def select_best_cohorts(possible_cohorts, num_cohorts, min_size, facilitators_info):
    """Select the best cohorts based on the number of participants and facilitator availability."""

    # First, check if it's feasible to form the requested number of cohorts
    if not is_feasible(possible_cohorts, num_cohorts, min_size, facilitators_info):
        raise ValueError("Unable to form the requested number of cohorts with the given parameters. Please adjust the parameters.")

    # Priority is given to larger cohorts (more participants)
    def cohort_priority(cohort):
        return len(cohort[2])

    sorted_cohorts = sorted(possible_cohorts, key=cohort_priority, reverse=True)

    # Create a dictionary to track the remaining capacity of each facilitator
    facilitator_capacity = {facilitator: info[1] for facilitator, info in facilitators_info.items()}

    # Check if the facilitator is available for the given cohort time
    def is_facilitator_available(facilitator, cohort_time):
        return any(start <= cohort_time[0] and end >= cohort_time[1] for start, end in facilitators_info[facilitator][0])

    # Iterate through facilitators and assign the first available one with enough capacity
    def assign_facilitator(cohort_time):
        for facilitator in facilitator_capacity:
            if facilitator_capacity[facilitator] > 0 and is_facilitator_available(facilitator, cohort_time):
                facilitator_capacity[facilitator] -= 1
                return facilitator
        return None

    def backtrack(selected, remaining):

        # If the desired number of cohorts is reached, return the selection
        if len(selected) == num_cohorts:
            return selected
        
        # If there are no more cohorts to consider, return None
        if not remaining:
            return None

        current_cohort = remaining[0]
        updated_remaining = remaining[1:]

        # Try to assign a facilitator to the current cohort
        facilitator = assign_facilitator((current_cohort[0], current_cohort[1]))
        if facilitator:
            updated_selected = selected + [(current_cohort[0], current_cohort[1], current_cohort[2], facilitator)]
            selected_names = {name for _, _, cohort, _ in updated_selected for name in cohort}
            next_remaining = [
                c for c in updated_remaining
                if not any(name in selected_names for name in c[2]) and len(c[2]) >= min_size
            ]

            result = backtrack(updated_selected, next_remaining)
            if result:
                return result

            # If this path doesn't lead to a solution, backtrack and restore the facilitator's capacity
            facilitator_capacity[facilitator] += 1

        # Try excluding the current cohort
        return backtrack(selected, updated_remaining)

    # Start the backtracking process with an empty selection and the sorted list of cohorts
    return backtrack([], sorted_cohorts) or []


def process_data(file_path, num_cohorts, min_size, max_size, time_block, facilitator_file_path, facilitator_capacity_entries={}):
    """
    Processes data to form cohorts based on participant and facilitator availabilities.

    Args: (these are the parameters that are passed in from the GUI)
        file_path (str): Path to the participant data file.
        num_cohorts (int): Number of cohorts to form.
        min_size (int): Minimum size of each cohort.
        max_size (int): Maximum size of each cohort.
        time_block (float): Duration of each time block in hours.
        facilitator_file_path (str): Path to the facilitator data file.
        facilitator_capacity_entries (dict): Entries of facilitator capacities.

    Returns:
        dict: A dictionary containing formed cohorts, participants not selected, and participants not available.
    """
    try:
        # Load participant data from JSON file
        with open(file_path, 'r') as file:
            data = json.load(file)

        # Load facilitator data from JSON file
        with open(facilitator_file_path, 'r') as file:
            facilitator_data = json.load(file)

        facilitators_availabilities = extract_facilitator_availabilities(facilitator_data)

        # Construct a dictionary of facilitators' info (availabilities and capacities)
        facilitators_info = {name: (facilitators_availabilities[name], int(facilitator_capacity_entries[name].get())) for name in facilitators_availabilities}
        
        # Extract participant availabilities and possible times for the event
        availabilities, possible_times, not_available = extract_participant_availabilities(data, time_block)
        
        # Find all possible cohorts based on availabilities and constraints
        all_cohorts = find_all_possible_cohorts(availabilities, facilitators_info, min_size, max_size, time_block, possible_times)

        # Select the best cohorts based on the number of participants and facilitator availability
        best_cohorts = select_best_cohorts(all_cohorts, num_cohorts, min_size, facilitators_info)

        # Return the results: the formed cohorts, participants not selected, and participants not available
        return {
            "cohorts": best_cohorts,
            "not_selected": set(availabilities.keys()) - set([name for cohort in best_cohorts for name in cohort[2]]),
            "not_available": not_available
        }

    except Exception as e:
        raise e
    


if __name__ == "__main__":
    file_path = "Cohort-Formation-LettuceMeet/anonymized_file.json"
    num_cohorts = 4
    min_size = 3
    max_size = 6 
    time_block = 1.5
    facilitator_file_path = "Cohort-Formation-LettuceMeet/facilitator_test.json"
    with open(facilitator_file_path, 'r') as file:
            facilitator_data = json.load(file)
    facilitator_names = extract_facilitator_availabilities(facilitator_data, names=True) 
    print(facilitator_names)
    facilitator_capacity_entries = {}
    for name in facilitator_names:
        facilitator_capacity_entries[name] = 1

    data = process_data(file_path, num_cohorts, min_size, max_size, time_block, facilitator_file_path, facilitator_capacity_entries)
    print(data)