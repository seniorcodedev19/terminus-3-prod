The summariser at /app/src/summarize.py is wrong. It runs, but the report it writes at /app/out/report.json does not match what the downstream process expects.

Rebuild /app/out/report.json for the .txt files under /app/data. The report is a JSON object with two top-level keys: "files", an array with one entry per .txt file — each entry an object with "name" (the filename) and "words" (its word count) — ordered by name; and "total_words", the sum of every file's word count. Serialize it with a two-space indent and end the file with a trailing newline.

Keep it driveable the way CI drives it: the program stays at /app/src/summarize.py and is run as `python3 /app/src/summarize.py --data <dir> --out <file>`. CI points it at directories other than the one shipped here.




