# Cohort-Formation-LettuceMeet

This repository facilitates the creation of cohorts from applicant availabilities submitted through LettuceMeet, specifically designed for groups organizing AI Safety Fundamentals courses in 2024 as part of the AI Safety Collab. However, with small modifications, it can be adapted for other programs or courses.

With many applicants in a LettuceMeet form it can be quite a frustrating process to create cohorts, as you can't select more than a half-hour block at a time while displaying which applicants are available. This script is meant to make that process easier. I have tried to make it as easy to use as possible for people who are not very familiar with Python, and the steps are outlined below for guidance. If you run in to any issues, or have suggestions for improvements, feel free to shoot me a message on slack at Victor Wellsmo. 

### Step 1: Download respository
At the top of this page, press the green "<> Code" button, and then "Download ZIP" in the dropdown menu. Unzip the files in your preferred directory.

### Step 2: Extracting availability data from LettuceMeet
The extraction process might vary slightly across different operating systems and browsers, but the differences should be small and solutions easily found online. Here's how to do it in Safari on a Mac:

1. Visit the LettuceMeet page showing registered availabilities.
2. In the menu bar, click “Develop”, then “Show Web Inspector”. (Enable “Develop” in the menu if it's not visible, following [these instructions](https://support.apple.com/en-il/guide/safari/sfri20948/mac).
3. Within the Web Inspector, go to the “Network” tab.
4. Look for entries titled “graphql” under “Names”. Refresh the page if needed to spot the right entry, which should resemble the format illustrated below:
<img src="https://github.com/Vicwel1/Cohort-Formation-LettuceMeet/assets/124055472/aa788931-3453-4c5e-99b5-038fff384aa1" width="80%">

5. Copy the content in full and save it as a .json file (e.g., "participant_availabilities.json") in the directory where you'll execute the Python script. For a template, refer to [this anonymized file](anonymized_file.json) from previous applications to AI Safety Gothenburg.

If you haven't already, make a separate LettuceMeet with entries for each of your group's facilitators time-availabilities. In the same way as for the applicants, make a .json file from the data (e.g. facilitator_availabilities.json). The dates for facilitators' availabilities don't need to match those of the participants; matching is based on weekdays and times.

### Step 3: Generating cohorts
There are two different ways to generate cohorts. 

#### For homogeneous applications:
  
If your LettuceMeet data contains applicants for only one course, you can use cohort_formation_GUI.py. This script requires no modifications; simply run it to open a user interface as shown below: 

<img width="40%" alt="windowgui" src="https://github.com/Vicwel1/Cohort-Formation-LettuceMeet/assets/124055472/2b1848f0-3778-41b4-9bc1-aa15da15b110">

When you have uploaded the facilitator file, each facilitator's name will show up with a box box where you can enter their capacity, i.e. how many cohorts they can facilitate.
Once all the fields are filled in, click "Generate cohorts" to execute the algorithm. The output will appear as demonstrated:

<img width="50%" alt="windowguiResults" src="https://github.com/Vicwel1/Cohort-Formation-LettuceMeet/assets/124055472/53020881-d1cf-49d2-9f24-360c7e0bd582">

#### For varied applications:
  
If your LettuceMeet data contains applicants for both alignment and governance, use cohort_formation_noGUI.py. This script necessitates edits to specific lines at the bottom of the file, highlighted in the image below. Adjust these lines according to the specifics for your group.

<img width="80%" alt="codeModify" src="https://github.com/Vicwel1/Cohort-Formation-LettuceMeet/assets/124055472/beeaad88-9a89-4979-8fc7-c3abbd20bb2d">




