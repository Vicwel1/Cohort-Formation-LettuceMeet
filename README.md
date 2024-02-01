# Cohort-Formation-LettuceMeet

## Purpose and use

With many applicants in a LettuceMeet form it can be quite a frustrating process to create cohorts, as you can't select more than a half-hour block at a time while displaying which applicants are available. This script is meant to make that process easier.

## Extracting availability data from LettuceMeet
I’m not sure how much this differs between operating systems and browsers, but I think it’s similar (and easy to google). Here is how I do it in Safari.
For Safari on Mac
1. Open the LettuceMeet page displaying registered time availabilities.
2. Click on “Develop” in the menu bar, then select “Show Web Inspector”. (If you don't see “Develop”, follow [these instructions](https://support.apple.com/en-il/guide/safari/sfri20948/mac).
3. In the Web Inspector, navigate to the “Network” tab.
4. Look for entries named “graphql” under “Names”. You might need to refresh the page to see the correct entry. The one you're looking for should match the format shown below:

<p align="center">
  <img src="LettuceMeetgraphql.pdf" width="400" title="Format of the graphql to locate">
</p>
5. Copy the full contents, and paste it in a .json file, in the same directory as you will run the python script.

## Generating cohorts

