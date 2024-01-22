import json
from datetime import datetime, timedelta
from itertools import combinations
from prettytable import PrettyTable



def extract_participant_availabilities(data, time_block, skip_list=[]):
    """Extract time availabilities for each applicant."""
    print("Extracting participant availabilities...")
    participants_availabilities = {}
    not_available = []

    possible_times = []
    pollStartTime = data['data']['event']['pollStartTime']
    pollEndTime = data['data']['event']['pollEndTime']
    pollDates = data['data']['event']['pollDates']
    for date in pollDates:
        possible_times.append((datetime.strptime(date + "T" + pollStartTime, "%Y-%m-%dT%H:%M:%S.%fZ"), datetime.strptime(date + "T" + pollEndTime, "%Y-%m-%dT%H:%M:%S.%fZ")))

    for response in data['data']['event']['pollResponses']:
        applicant_name = response['user']['name']
        if applicant_name in skip_list:
            print(f'Skipping {applicant_name}')
            continue
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

        participants_availabilities[applicant_name] = time_slots

    return participants_availabilities, possible_times, not_available

def extract_facilitator_availabilities(data, names=False):
    facilitators_availabilities = {}
    facilitator_names = []
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
    if names:
        return facilitator_names
    else:
        return facilitators_availabilities

def find_all_possible_cohorts(participants_availabilities, facilitators_availabilities, min_cohort_size, max_cohort_size, time_block, possible_times):
    possible_cohorts = []
    for day in possible_times:
        start_time = day[0]
        end_time = day[1]
        current_time = start_time
        while current_time + timedelta(hours=time_block) <= end_time:
            slot_end_time = current_time + timedelta(hours=time_block)

            available_facilitators = [
                f for f in facilitators_availabilities
                if any(s <= current_time and e >= slot_end_time for s, e in facilitators_availabilities[f][0]) and facilitators_availabilities[f][1] > 0
            ]
            if not available_facilitators:
                current_time += timedelta(minutes=30)
                continue

            available_participants = [
                p for p in participants_availabilities
                if any(s <= current_time and e >= slot_end_time for s, e in participants_availabilities[p])
            ]
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

    if not is_feasible(possible_cohorts, num_cohorts, min_size, facilitators_info):
        raise ValueError("Unable to form the requested number of cohorts with the given parameters. Please adjust the parameters.")

    def cohort_priority(cohort):
        # Priority based on the number of participants
        return len(cohort[2])

    sorted_cohorts = sorted(possible_cohorts, key=cohort_priority, reverse=True)

    facilitator_capacity = {facilitator: info[1] for facilitator, info in facilitators_info.items()}

    def is_facilitator_available(facilitator, cohort_time):
        # Check if the facilitator is available for the given cohort time
        return any(start <= cohort_time[0] and end >= cohort_time[1] for start, end in facilitators_info[facilitator][0])

    def assign_facilitator(cohort_time):
        # Try to find an available facilitator with capacity
        for facilitator in facilitator_capacity:
            if facilitator_capacity[facilitator] > 0 and is_facilitator_available(facilitator, cohort_time):
                facilitator_capacity[facilitator] -= 1
                return facilitator
        return None

    def backtrack(selected, remaining):
        if len(selected) == num_cohorts:
            return selected

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

            # Backtrack: Restore facilitator capacity
            facilitator_capacity[facilitator] += 1

        # Try excluding the current cohort
        return backtrack(selected, updated_remaining)

    return backtrack([], sorted_cohorts) or []


def process_data(file_path, num_cohorts, min_size, max_size, time_block, facilitator_file_path, facilitator_capacity_entries={}):
    try:
        with open(file_path, 'r') as file:
            data = json.load(file)

        with open(facilitator_file_path, 'r') as file:
            facilitator_data = json.load(file)
        facilitators_availabilities = extract_facilitator_availabilities(facilitator_data)

        #facilitator availability in the form of a dictionary where keys are facilitator names and values are tuples of their available time slots and remaining capacities.
        facilitators_info = {name: (facilitators_availabilities[name], int(facilitator_capacity_entries[name].get())) for name in facilitators_availabilities}
        
        skip_list = []
        availabilities, possible_times, not_available = extract_participant_availabilities(data, time_block, skip_list=skip_list)
        
        all_cohorts = find_all_possible_cohorts(availabilities, facilitators_info, min_size, max_size, time_block, possible_times)
        best_cohorts = select_best_cohorts(all_cohorts, num_cohorts, min_size, facilitators_info)

        return {
            "cohorts": best_cohorts,
            "not_selected": set(availabilities.keys()) - set([name for cohort in best_cohorts for name in cohort[2]]),
            "not_available": not_available
        }
        # # Format and return the results
        # result = ""
        # for i, cohort in enumerate(best_cohorts, start=1):
        #     start, end, participants, facilitator = cohort
        #     start_str = start.strftime('%A, %H:%M')
        #     end_str = end.strftime('%H:%M')
        #     # result += f"Cohort {i}, {start_str} to {end_str}\n" + ", ".join(participants) + "\n\n"
        #     result += f"Cohort {i}, {start_str} to {end_str}\n" + ", ".join(participants) + f"\n Facilitator: {facilitator} \n\n"

        # if not_selected := set(availabilities.keys()) - set([name for cohort in best_cohorts for name in cohort[2]]):
        #     result += "Applicants not included in cohorts:\n" + "\n".join(not_selected)
        
        # result += f"\n\nApplicants skipped due to low availability (available less than {time_block} hours in a row):\n" + "\n".join(not_available)

        # return result

    except Exception as e:
        raise e