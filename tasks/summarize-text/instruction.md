The summariser at /app/src/summarize.py is wrong. It runs, but the report it writes at /app/out/report.json does not match what the downstream process expects.

Rebuild /app/out/report.json for the .txt files under /app/data. The report is a JSON object with two top-level keys, in this order: "files" then "total_words". "files" is an array with one entry per .txt file, ordered by name; each entry is an object with "name" (the filename) followed by "words" (its word count), in that order. "total_words" is the sum of every file's word count. Only regular files count — a directory whose name happens to match *.txt is not a file. Serialize it with a two-space indent and end the file with a trailing newline.

Keep it driveable the way CI drives it: the program stays at /app/src/summarize.py and is run as `python3 /app/src/summarize.py --data <dir> --out <file>`. CI points it at directories other than the one shipped here.




