# This file contains the code for the cohort formation algorithm with no GUI. You only need to modify the parameters at the bottom of the file.

import json
from datetime import datetime, timedelta
from itertools import combinations



def extract_participant_availabilities(data, time_block, alignment_applicants, governance_applicants, filter_by_course):
    """Extract time availabilities for each applicant."""
    alignment_availability = {}
    governance_availability = {}
    misc_availabilities = {}
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

        # Convert availability times to datetime objects
        time_slots = [
            (
                datetime.strptime(availability['start'], "%Y-%m-%dT%H:%M:%S.%fZ"),
                datetime.strptime(availability['end'], "%Y-%m-%dT%H:%M:%S.%fZ")
            )
            for availability in response['availabilities']
        ]


        if not any(e-s >= timedelta(hours=time_block) for s, e in time_slots):
            not_available.append(applicant_name)
            continue

        if filter_by_course:
            if applicant_name in alignment_applicants:
                alignment_availability[applicant_name] = time_slots
            elif applicant_name in governance_applicants:
                governance_availability[applicant_name] = time_slots
            else:
                misc_availabilities[applicant_name] = time_slots
        else:
            participants_availabilities[applicant_name] = time_slots

    if filter_by_course:
        return [alignment_availability, governance_availability, misc_availabilities], possible_times, not_available
    else:
        return participants_availabilities, possible_times, not_available


def match_dates(facilitator_data, participant_data):
    """
    Match the dates of the facilitator and participant data. This is done so that the facilitator and participant availabilities can be compared, 
    even if the facilitator and participant poll dates are different.
    Returns a dictionary mapping facilitator dates to participant dates.
    """
    date_mapping = {}
    pollDates_facilitator = facilitator_data['data']['event']['pollDates']
    pollDates_participant = participant_data['data']['event']['pollDates']
    weekdays_participant = [datetime.strptime(date, "%Y-%m-%d").weekday() for date in pollDates_participant]
    for date in pollDates_facilitator:
        weekday = datetime.strptime(date, "%Y-%m-%d").weekday()
        index = weekdays_participant.index(weekday)
        date_mapping[date] = pollDates_participant[index]
    
    return date_mapping


def extract_facilitator_availabilities(facilitator_data, participant_data):
    """Extract facilitator availabilities from the data"""

    facilitators_availabilities = {}
    date_mapping = match_dates(facilitator_data, participant_data)


    # Iterate through each response and extract facilitator availabilities
    for response in facilitator_data['data']['event']['pollResponses']:
        facilitator_name = response['user']['name']
        time_slots = []
        for availability in response['availabilities']:
            # Convert availability times to datetime objects
            start = datetime.strptime(availability['start'], "%Y-%m-%dT%H:%M:%S.%fZ")
            end = datetime.strptime(availability['end'], "%Y-%m-%dT%H:%M:%S.%fZ")
            # convert the date to the participant date
            start_date = datetime.strptime(date_mapping[str(start.date())], "%Y-%m-%d")
            end_date = datetime.strptime(date_mapping[str(end.date())], "%Y-%m-%d")

            start = start.replace(year=start_date.year, month=start_date.month, day=start_date.day)
            end = end.replace(year=end_date.year, month=end_date.month, day=end_date.day)
            time_slots.append((start, end))
            
        facilitators_availabilities[facilitator_name] = time_slots

    return facilitators_availabilities


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


def print_cohorts(data):
    """
    Print the formed cohorts and participants not selected.
    data: dictionary containing the formed cohorts, participants not selected, and participants not available

    """
    result_text = ""
    # check if there is a misc cohort key
    if "misc cohorts" in data:
        for i, cohort in enumerate(data["misc cohorts"], start=1):
            start, end, participants, facilitator = cohort
            start_str = start.strftime('%A, %H:%M')
            end_str = end.strftime('%H:%M')
            result_text += f"Cohort {i}, {start_str} to {end_str}\n"
            result_text += ", ".join(participants) + f"\n"
            result_text += f"Facilitator: "
            result_text += f"{facilitator}\n\n"
        if data["not_selected_misc"]:
            result_text += "Applicants not included in cohorts:\n"
            for applicant in data["not_selected_misc"]:
                result_text += f"{applicant}\n"
        if data["not_available"]:
            result_text += f"\nApplicants skipped due to low availability (available less than {time_block} hours consecutively):\n"
            for applicant in data["not_available"]:
                result_text += f"{applicant}\n"
        print(result_text)
    else:
        for i, cohort in enumerate(data["align cohorts"], start=1):
            start, end, participants, facilitator = cohort
            start_str = start.strftime('%A, %H:%M')
            end_str = end.strftime('%H:%M')
            result_text += f"Alignment cohort {i}, {start_str} to {end_str}\n"
            result_text += ", ".join(participants) + f"\n"
            result_text += f"Facilitator: "
            result_text += f"{facilitator}\n\n"
        for i, cohort in enumerate(data["gov cohorts"], start=1): 
            start, end, participants, facilitator = cohort
            start_str = start.strftime('%A, %H:%M')
            end_str = end.strftime('%H:%M')
            result_text += f"Governance cohort {i}, {start_str} to {end_str}\n"
            result_text += ", ".join(participants) + f"\n"
            result_text += f"Facilitator: "
            result_text += f"{facilitator}\n\n"
        if data["not_selected_align"]:
            result_text += "Alignemnt applicants not included in cohorts:\n"
            for applicant in data["not_selected_align"]:
                result_text += f"{applicant}\n"
        if data["not_selected_gov"]:
            result_text += "\nGovernance applicants not included in cohorts:\n"
            for applicant in data["not_selected_gov"]:
                result_text += f"{applicant}\n"
        if data["not assigned to alignment or governance"]:
            result_text += "Applicants not assigned to alignment or governance:\n"
            for applicant in data["not assigned to alignment or governance"]:
                result_text += f"{applicant}\n"
        if data["not_available"]:
            result_text += f"\nApplicants skipped due to low availability (available less than {time_block} hours consecutively):\n"
            for applicant in data["not_available"]:
                result_text += f"{applicant}\n"
        print(result_text)


def process_data(params):
    """
    Process the data and return the results.
    
    Parameters:
    - file_path: path to the JSON file containing the participant data
    - num_align_cohorts: number of alignment cohorts to form
    - num_gov_cohorts: number of governance cohorts to form
    - num_total_cohorts: total number of cohorts to form (used when not filtering by course)
    - min_size: minimum number of participants in a cohort
    - max_size: maximum number of participants in a cohort
    - time_block: meeting time block in hours
    - facilitator_file_path: path to the JSON file containing the facilitator data
    - facilitator_capacity_course_entries: dictionary containing the facilitator's capacity and course
    - alignment_applicants: list of applicants who applied for alignment
    - governance_applicants: list of applicants who applied for governance
    - filter_by_course: boolean indicating whether to filter by course or not

    """

    try:
        participant_file_path = params["participant_file_path"]
        num_align_cohorts = params["num_align_cohorts"]
        num_gov_cohorts = params["num_gov_cohorts"]
        num_total_cohorts = params["num_total_cohorts"]
        min_size = params["min_size"]
        max_size = params["max_size"]
        time_block = params["time_block"]
        facilitator_file_path = params["facilitator_file_path"]
        facilitator_capacity_course_entries = params["facilitator_capacity_course_entries"]
        alignment_applicants = params["alignment_applicants"]
        governance_applicants = params["governance_applicants"]
        filter_by_course = params["filter_by_course"]

        # Load participant data from JSON file
        with open(participant_file_path, 'r') as file:
            participant_data = json.load(file)

        # Load facilitator data from JSON file
        with open(facilitator_file_path, 'r') as file:
            facilitator_data = json.load(file)

        facilitators_availabilities = extract_facilitator_availabilities(facilitator_data, participant_data)

        
        facilitators_info = {name: [facilitators_availabilities[name], int(facilitator_capacity_course_entries[name][0]), facilitator_capacity_course_entries[name][1]] for name in facilitators_availabilities}
        
        # Extract participant availabilities and possible times for the event
        availabilities, possible_times, not_available = extract_participant_availabilities(participant_data, time_block, alignment_applicants, governance_applicants, filter_by_course)

        if filter_by_course:
            align_facilitators_info = {name: [facilitators_availabilities[name], int(facilitator_capacity_course_entries[name][0])] for name in facilitators_availabilities if facilitator_capacity_course_entries[name][1] == "align"}
            gov_facilitators_info = {name: [facilitators_availabilities[name], int(facilitator_capacity_course_entries[name][0])] for name in facilitators_availabilities if facilitator_capacity_course_entries[name][1] == "gov"}

            alignment_availability = availabilities[0]
            governance_availability = availabilities[1]
            misc_availabilities = availabilities[2]

            if alignment_availability:
                all_align_cohorts = find_all_possible_cohorts(alignment_availability, align_facilitators_info, min_size, max_size, time_block, possible_times)
                best_align_cohorts = select_best_cohorts(all_align_cohorts, num_align_cohorts, min_size, align_facilitators_info)
                not_selected_align = set(alignment_availability.keys()) - set([name for cohort in best_align_cohorts for name in cohort[2]])

            if governance_availability:
                all_gov_cohorts = find_all_possible_cohorts(governance_availability, gov_facilitators_info, min_size, max_size, time_block, possible_times)
                best_gov_cohorts = select_best_cohorts(all_gov_cohorts, num_gov_cohorts, min_size, gov_facilitators_info)
                not_selected_gov = set(governance_availability.keys()) - set([name for cohort in best_gov_cohorts for name in cohort[2]])

            return {
                'align cohorts': best_align_cohorts,
                'gov cohorts': best_gov_cohorts,
                'not_selected_align': not_selected_align,
                'not_selected_gov': not_selected_gov,
                'not assigned to alignment or governance': misc_availabilities.keys(),
                'not_available': not_available,
            }
        else:
            participants_availabilities = availabilities
            all_cohorts = find_all_possible_cohorts(participants_availabilities, facilitators_info, min_size, max_size, time_block, possible_times)
            best_cohorts = select_best_cohorts(all_cohorts, num_total_cohorts, min_size, facilitators_info)
            not_selected = set(participants_availabilities.keys()) - set([name for cohort in best_cohorts for name in cohort[2]])
            return {
                'misc cohorts': best_cohorts,
                'not_selected_misc': not_selected,
                'not_available': not_available,
            }

    except Exception as e:
        raise e
    


if __name__ == "__main__":
    """
    This is the main function that runs the cohort analysis. You only need to modify the parameters below.
    
    """

    # File path to the JSON file containing the participant data from LettuceMeet (Instructions for generating this file can be found in the README)
    participant_file_path = "Cohort-Formation-LettuceMeet/anonymized_file.json"

    # File path to the JSON file containing the facilitator data from LettuceMeet (Instructions for generating this file can be found in the README)
    facilitator_file_path = "Cohort-Formation-LettuceMeet/facilitator_test.json"

    # Minimum and maximum number of participants in a cohort
    min_size = 4
    max_size = 6

    # Meeting time block in hours
    time_block = 1.5

    # Set to True if you want to filter by course, False otherwise. If True, modify the lists of alignment and governance applicants below. 
    # If False, modify the number of total cohorts to form, under the variable num_total_cohorts.
    filter_by_course = True

    # Enter the facilitator's capacity (number of cohorts) and course in the format facilitator_name: [capacity, course], with course being either "align" or "gov". 
    # If filter_by_course is set to False, the course choice will be ignored, so you can set it to anything.
    facilitator_capacity_course_entries = {
        'facilitator1': [1, "align"],
        'facilitator2': [2, "gov"],
        'facilitator3': [2, "align"],
        'facilitator4': [1, "align"],
    }


    # If you set filter_by_course to True, modify the entries below.
    num_align_cohorts = 4
    num_gov_cohorts = 2

    # Names of the applicants who applied for alignment
    alignment_names = ['Participant_9815', 'Participant_8903', 'Participant_4697', 'Participant_4252', 'Participant_1341', 
                    'Participant_5185', 'Participant_1058', 'Participant_4268', 'Participant_3411', 'Participant_5607', 
                    'Participant_3569', 'Participant_8043', 'Participant_3020', 'Participant_7441', 'Participant_8474', 
                    'Participant_1885', 'Participant_3866', 'Participant_5060', 'Participant_2590', 'Participant_4674', 
                    'Participant_7913', 'Participant_5398', 'Participant_6732', 'Participant_1212', 'Participant_7176', 'Participant_2122']
    
    # Names of the applicants who applied for governance
    governance_names = ['Participant_8148', 'Participant_6002', 'Participant_5263', 'Participant_8951', 'Participant_6396', 
                            'Participant_8419', 'Participant_9931', 'Participant_9400', 'Participant_9497', 'Participant_9371', 
                            'Participant_7496', 'Participant_6966']

    # If you set filter_by_course to False, modify the toal number of cohorts below.
    num_total_cohorts = 6

    
    
    params = {
        "participant_file_path": participant_file_path,
        "num_align_cohorts": num_align_cohorts,
        "num_gov_cohorts": num_gov_cohorts,
        "num_total_cohorts": num_total_cohorts,
        "min_size": min_size,
        "max_size": max_size,
        "time_block": time_block,
        "facilitator_file_path": facilitator_file_path,
        "facilitator_capacity_course_entries": facilitator_capacity_course_entries,
        "alignment_applicants": alignment_names,
        "governance_applicants": governance_names,
        "filter_by_course": filter_by_course,
    }

    data = process_data(params)
    print_cohorts(data)
    