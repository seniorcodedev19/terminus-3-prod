@channel IMPORTANT: Major Quality Panel Update — Please Read Before Your Next Submission :alert: :alert:

Docs update: Quality panel judge — author guide is up

The quality panel is an automated review of the task you built, not of an agent run. After you submit, and before a human reviewer picks it up, it reads instruction.md, task.toml, environment/, solution/, and tests/ and asks whether the task is a fair, closed problem: disclosed rules, a reference that actually matches those rules, answers that cannot be stolen from the grader, and tests that fail if the work is not done.

The four axes:

• coherent_contract — Could two competent people, given only what the candidate sees, reasonably disagree on a graded answer? Every rule the grader enforces needs a citable sentence (or a fully deterministic artifact the contract points at)..
• correct_reference_solution — Does your reference satisfy that contract on the edges, not only the happy path? Format/width, loop-carried state, and “the formula looks right” misses show up here..
• protected_ground_truth — Can a candidate reach, forge, or infer the expected answer instead of computing it? A golden file is only a finding if it is actually reachable and knowable from candidate-visible material. Separate environment_mode hides goldens from the agent container; it does not hide them from agent code the verifier itself executes..
• sound_verifier — Could a genuine attempt pass tests/ without solving the task? Incomplete coverage and trusting a channel the candidate controls (exit code, shared stdout, an invocable oracle) are the usual hits..
Minor and Major both block, the same way a failing CI check does. The label is how serious the defect is, not whether you can ignore it. Unsure also blocks: the panel could not finish a verdict, so a human looks — that is not a confirmed defect in your task. Only None on every axis auto-accepts.

This does not replace Writing Tests, Dockerfile Requirements, or a human reviewer.

Walk the checklist before you submit so a Minor/Major is not a surprise. Numbered worked cases are synthetic composites in a separate appendix; they are not excerpts from anyone’s submission.

Full detail:

• Guide: https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/testing-and-validation/quality-panel-judge-guide.
• Appendix: https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/testing-and-validation/quality-panel-examples.
• If a cited finding looks wrong: https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/reviewing-tasks/defending-your-submission.

-------------
@channel Docs + new CI check: two Dockerfile patterns that work locally will now fail at submit

The cloud image builder rejects two bits of syntax that local Docker accepts. A blocking CI check now flags them immediately (exact line + replacement) so you don’t wait on a long eval. Docs: Cloud Image Builder Syntax

Fix these if you use them (every Dockerfile: environment/, tests/, extras):
1. COPY --chown= must be numeric IDs
   COPY --chown=root:root … / COPY --chown=appuser:appuser … → COPY --chown=0:0 … or COPY --chown=1000:1000 …

2. COPY --from= image refs must be digest-only
   COPY --from=golang:1.24-bookworm@sha256:… → COPY --from=golang@sha256:…
   Drop the :tag, keep the digest.

Unchanged — don’t “fix” these:
- FROM image:tag@sha256:… is still the required pin form
- COPY --from=builder (stage names) is fine
- RUN chown is unchanged

Known Modal quirk: COPY --chown=UID:GID dest chowns contents only, not dest itself (on Docker both are chowned). If a later RUN creates files under that directory (mkdir, Maven target/, etc.) and you get Permission denied, add RUN chown UID:GID dest immediately after the COPY. RUN chown is allowed.

Full detail:

• Checklist: Submission Checklist .
• FAQ: Preflight failed on COPY --chown / COPY --from.

--------------------
@channel we need to start tracking when people are not working in their home location going forward. This not only protects you from removal, but allows us to stay in compliance. If you are working outside your home country, could you DM me with where you're working and what the dates are? We will need this information going forward, so if you have travel planned as well, let me know that!

---------------------
@channel our engineering team has been working tirelessly to get the evals unblocked. While it has not cleared the queue 100% we are pleased to inform you it is starting to work! We have over 900 tasks in "Needs Revision" currently - so if you haven't logged on in a while - please check your queue and get those tasks revised as soon as you can!

If you see your task still stuck in eval_pending this is expected since as I said above, it is not 100% clear yet. Please continue to practice patience as we work to completely clear the backlog. Please do not DM or message in the channel about blocked evals.

---------------------
@channel We are making an adjustment to the task guidelines that is effective immediately. This will apply to all new tasks and tasks in progress. Going forward, it will be required that the network_mode = public line is in the [environment] section of task.tomls for tasks. You can continue to specify that agent and verifier are no-network or public individually per the author choice.


Example shape in task.toml:

[environment]
network_mode = "public"

[agent]
network_mode = "no-network"

[verifier]
network_mode = "no-network"

------------------------
@channel

:redsiren:Eval issue resolved — action needed on your tasks:redsiren:

Thanks for your patience this past week while we worked through the eval problem. It's now fixed.

The catch: the only way to clear your tasks out of their failed eval state is to send them back to you as revisions. You'll see those coming through shortly.

When your task lands:

1. Give it a quick review to confirm it's still compliant with our most recent updates (the task skeleton is now available too!).
2. Send it back into the queue.

Evals should run cleanly from there. Reach out if anything seems off and thank you for your patience once again!


Your task will show "rejected" in the payment section. This is expected. It will update once your task is re-accepted and is paid out.

----------------------------
@channel

:hammer_and_wrench: :bug: As our team continues to resolve the quality eval issues on platform (again our goal is by EOW/EOD Friday), we wanted to share :memo:  additional guidelines :memo: in the meantime. We will work on getting this added to our website as well.

Additional Guidelines to Help Keep Your Instruction, Tests & Solution in Sync (:pdf:  attached as a PDF file below) 

• :alert: These address the patterns behind almost every task we/Reviewers may send back: the six main places where the instruction, tests, and solution most often drift apart, each with a set of quick self-check notes provided by our team, plus a 60-second pre-submit audit. .
◦ Give it a read before your next submission, and use it as the reference as you go through the feedback on your task..
• For example, a passing oracle doesn't mean your tests are solid, could a deliberately wrong solution also pass them? If yes, then these notes are definitely relevant to improving your work!.

EDIT: Some of you may have have gotten a completed task sent back - we will require you to fix those issues. Much of those issues are covered throughout this document. For everyone else, you should still read this as your tasks in the future may get returned for same issues.

---------------------------
@channel an update about the evals and their failures:

• fixing one bug has uncovered another, so this is not yet fixed. .
• please make sure you add all eval-failure tasks to the announcement in the submissions channel.

We hope to have this fixed by Friday but we thank you for your patience while we work through it!

----------------------------
@channel :mega: Difficulty runs have changed — new two-stage model :mega: 

Difficulty is now measured in two stages, with different run counts.

While you're iterating (in-platform)
• 2 runs per model × 2 models = 4 runs
• At least one of those 4 must fail for the task to proceed to review
• Both models always run now — the old "early exit" that skipped the second model is gone

After a reviewer accepts your task
• 4 runs per model × 2 models = 8 runs
• This is what sets your final tier — it can differ from what you saw while iterating

What this means in practice
:one: If every run passes, you can't submit. A task all 4 runs solve gives no signal about agent
capability. Make it genuinely harder — don't just tighten a numeric threshold, which shows up as a
near_miss flag rather than real difficulty.

:two: The tier you see while iterating is provisional. It comes from 4 runs, not 8.

:three: Update your local commands — use -k 4 to mirror the final measurement:

stb harbor run -m @openai/gpt-5.6 -p <task-folder> -k 4
stb harbor run -m @anthropic/claude-opus-5 -p <task-folder> -k 4
Fewer runs are fine for a rough signal while you're still building.

Also worth knowing
• difficulty must use a current tier — frontier / advanced / core / base. The old
  easy / medium / hard names are retired and will be sent back.
• A known environment defect (missing dependency, environment that won't build, runtime network need
  under no-network) now blocks acceptance even if no run happened to fail because of it.

Full details :point_right: https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/understanding-tasks/difficulty-guidelines

----------------------------
@channel we have added a new bot to our submissions channel!  @Terminus Task Bot will now be available for you to ask about the current status of your tasks. It will let you know what it's status is as well as the last time it was submitted. Using it is easy:

• Ex: @Terminus Task Bot what is the current status of task UUID: XXXX.

The documentation is updated every hour, so if it is new, it may not have been added yet, give it some time. Let us know if you have any questions!


Update: It will only respond when tagged going forward, so if you need to check more tasks after your initial message, tag it again!

----------------------------
@channel we just want to remind you that you should be writing your tasks yourself. We have had several tasks flagged to us for suspected LLM generation. We will be monitoring these tasks. If you are caught using LLMs to generate your tasks, this could result in removal from the project as well as the platform.

----------------------------
@channel We've made a few updates to the project workflow that will affect how you submit tasks. These changes are designed to help us curate the best possible work and make sure everyone has a clear understanding of what the project requires, without overwhelming the pipeline.

We're excited about this next iteration, and we know you are too. That's exactly why we need your best work early on - it helps us prove this project's value and integrity, so it can keep going for the long haul.

What's changing:

• One task in revision at a time. You'll now be limited to a single task in your "needs_revision" queue. If you have more than one, you won't be able to submit new tasks until that's resolved..
◦ If you're stuck on a task in revision, you're welcome to discard it and move on to something new instead..
• New contributors: 2 pending tasks max. If you haven't had a task accepted yet, you'll be limited to 2 pending tasks at a time. This helps us ensure quality and confirm you're aligned with the project's expectations early on..

As always, feel free to reach out with any questions!

----------------------------
@channel if you have a task that causes an LLMaJ refusal, please drop the UUID in this thread so our team can investigate it. ONLY use this thread for refusals.

----------------------------
@channel - first and foremost: Welcome to Project Terminus 3. We're really happy to be continuing this frontier work with you all! Thank you (again) for all the hard work on Terminus 2nd Edition.

We'll plan to share more information tomorrow to help clarify major differences. We'll share a presentation/materials for you all to have handy + host some office hours tomorrow.

Justin... can we get to tasking?

:white_check_mark: The Terminus-3-Prod Pipeline is now OPEN!

• If you have taken and passed the Assessment, you should have gotten an email about it notifying you of next steps. .

:eyes: :alert: - Please read this before you post about it (please and thank you):

1. The agent review is still worked on by our team - Do not be alarmed about it for now.
2. :skeleton-vibe: - Task Skeletons? We'll share more throughout the week, we are building these. .

:dollar:

• Rate card schedule is in the email - but we'll get it linked on our site properly sooooon.

----------------------------
@channel Docs update: named verifier exploit patterns (Aug 19) :memo:

We just made an update that extends the Aug 17 “reject wrong solutions” guidance with the specific verifier failure modes showing up most in recent delivery review (~half of tasks flagged on verifier soundness). This is not new policy — it names patterns authors and reviewers were already expected to catch, with concrete examples and checklist items.

For Submitters — check these before you submit
1. Goldens live in the verifier image, not agent-writable paths
Don’t derive expected bytes, corpus metadata, or held-out truth from /app, mutable corpora, or agent-delivered trees. Bake fixtures into tests/Dockerfile.
→ Writing Tests → Deriving Ground Truth from Agent-Writable Paths

2. Don’t stage agent directories yourself
Use top-level artifacts in task.toml and [verifier].environment_mode = "separate". Manual copytree of agent trees is a smell — symlinks can expose verifier goldens.
→ Writing Tests → Symlink and Copy Staging Leaks

3. Instruction tolerances must match test tolerances
If the instruction says “within 1e-3”, don’t assert 1e-9 in pytest.
→ Writing Tests → Instruction Tolerance Must Match Verifier Tolerance

4. Test the full objective and tie-breaks
When the spec says “minimize X, then Y”, feasibility-only checks aren’t enough — reject plans that optimize the wrong quantity. Spot-check the oracle on a case where two feasible answers differ.
→ Writing Tests → Optimization Objectives and Tie-Breaks
→ Writing Oracle Solution → Correct, Not Just Passing

5. Still required from Aug 17: run a deliberately wrong solution against your own verifier before submit. A passing oracle is not proof the reference is correct.
→ Submission Checklist
→ What Makes a Good Task

Full changelog: Welcome → Latest Updates

----------------------------
:loudspeaker: Pending Evaluation Issue Update
@channel We want to share an update on the pending_evaluation issue.

While things have improved over the last few days, the issue is not fully resolved yet. Some submissions may still remain stuck in pending_evaluation longer than expected, and in some cases evals may continue to fail before they can move forward to review.

We know this is frustrating and that it is slowing down your work. We hear you, and we are actively working with the Engineering team to get this fully resolved.

Thank you for continuing to stay patient and engaged while we work through this. We truly value the time, effort, and quality you are putting into Terminus 3, and we’ll keep sharing updates as we make progress.

----------------------------
@channel New platform preflight: verifier_interpreter_permissions*

If your verifier saves and restores permissions for both /bin/bash and /usr/bin/bash, those paths can be the same file on merged-/usr images. The second save can record mode 000. Cleanup then leaves Bash non-executable, and Harbor cannot collect verifier logs (DownloadVerifierDirError / Permission denied) even when pytest already wrote a reward.

The platform now flags that pattern before Oracle. A match is a blocking ERROR with file and line. It is *not* in stb harbor check. The matcher is only that dual-path restore — not a general ban on chmod.

Fix: Path.resolve() every path, deduplicate, restore each original mode once (do not hardcode 0755), and keep cleanup in try/finally. Then re-run a full Oracle in the target image and confirm log collection finishes.

Guide: https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/creating-tasks/writing-tests#preserve-interpreter-permissions
Check details: https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/testing-and-validation/ci-checks-reference#verifier-interpreter-permissions-platform-preflight

----------------------------
@channel - Hey all, we have an update/fix for the quality check not displaying fully: Quality judge log truncation fix incoming 

This should be fixed within the hour and you should now be able to see full logs.

In the meantime, you should still be able to view the full results since it is included in the difficult check logs as a panel review json file!

Let us know if you have any questions!

----------------------------
What looks like "platform errors" is actually expected behavior

We've seen a lot of messages about the platform throwing errors, so wanted to clear things up.

The platform is working as intended. The new checks are just tougher than what everyone's used to.

Why: we have to keep raising the bar on our checks to keep pace with customer demands (and judges that get smarter by the day). That's why we've pushed several checks upstream to you, we were seeing failures show up after a verdict had already been marked "accepted," which isn't a great experience for the customer.

A few clarifications on what's being tested:

• Oracle 3/3 — proves your reference solution passes your verifier.
• NOP 0/1 — proves doing nothing doesn't pass (together with your local agent/verifier runs, this confirms the task executes correctly as written).
• Quality Panel — a different check entirely: it asks whether a different implementation could slip past your verifier, and whether your Oracle actually holds up beyond the cases your tests cover.

Hope this clears some things up and as always, let us know if you have further questions!

----------------------------
Welcome to Terminus-3!

:snorkel: You passed the Terminus-3 Assessment. This means you are ready to fully contribute and submit tasks on the Terminus project. You should be fully onboarded now, but let me know if you are seeing errors.

:mag_right:How to find it: Navigate to your main dashboard on the Snorkel website. Under "My Projects" you'll see a project called Terminus-3-Prod (you may have to search for it if you have a lot of projects!) — click on the Submissions node to get started.

:question:If you need clarifications on anything, check the website.

:thought_balloon:You can also ask Terminus Bot (by tagging him in this channel) any time you have questions.

• remember proper bot etiquette is to start a thread (example: I have a question) and the nest your actual question/error log within the message while also tagging the bot. .

----------------------------
@channel here's how submission limits work :memo:


• Net-new submissions are capped at 3 per day..
• Daily limits reset at midnight UTC (~7–8 PM EST)..
• Only net-new submissions count — revisions do not count toward the daily limit..

So if you submitted 2 tasks yesterday and 1 today (all before the UTC reset), but the system shows 3 submissions from 08/05 UTC time, you've already hit the daily cap for that UTC day. The key detail is that the limit is based on the submitted_at timestamp in UTC — not your local timezone. A task you submitted "yesterday" in your local time may still fall on the same UTC date (08/05) if it was after midnight UTC.

You'll be able to submit again once the clock rolls past 00:00 UTC.

Also note: there's a separate revision-queue limit of 10 submissions max. If you ever hit 10 items in your revision queue, you're blocked from net-new submissions until you clear some (via revision or discard).

----------------------------
Hey @channel, we will get our website updated but you all may be seeing our updated check updates in place.


1. We have a task.toml updated version attached below. This means you may need to update your task. .
a. I am sorry for the inconveniences this causes, but I appreciate everyone's willingness to adjust the task. .

2.  Separately: Some of your tasks may get back as needs_revision in a bit as well if they are being flagged as TRIVIAL difficulty. Our systems/logs should now be reporting in the Terminus 3 language of difficulty, but if your task was TRIVIAL, it will get sent back in a bit!

----------------------------
@channel IMPORTANT: Major Quality Panel Update — Please Read Before Your Next Submission :alert: :alert:

Quality panel author guide is published (announcement has the full note).

Practical bits:

1. Read the renderedinstruction.md. Leftover repr() / template junk in Required outputs is a real coherent_contract hit..
2. Every rule your tests enforce needs a sentence the candidate can cite. If it only lives in solution/, that is a gap..
3. Separate environment_mode hides goldens from the agent container, not from agent code your verifier execs. Do not colocate goldens with paths you pass into that process..
4. Minor is not optional polish. It still comes back..

Full detail:

• Guide: https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/testing-and-validation/quality-panel-judge-guide .
• Examples: https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/testing-and-validation/quality-panel-examples.

----------------------------
:loudspeaker: Eval Failure Update
@channel We know many of you are seeing eval failures or submissions stuck in the queue. The team is aware and actively working on it.

A few updates:

• The eval queue is currently very large, so we are not able to manually retry failed evals at the moment..
• Some failures are tied to known platform / infrastructure issues, including LLM rate limits and recent backend changes..
• Engineering and Infra are working on fixes, but this may take some time to fully resolve..
• Since today is Labor Day, team availability may be limited, so we may not be able to fully resolve this by end of day..

For now, please be patient and avoid repeatedly resubmitting or posting the same IDs unless we specifically ask for them. We’ll continue monitoring the impacted submissions and will share updates once retries are available or the underlying issues are fixed.

We know this is frustrating and appreciate your patience while we work through it.

----------------------------
@channel
:bar_chart: Difficulty is now measured once — and you'll see the final tier before review
We've simplified how difficulty gets measured. The two-stage model is gone.

What changed
• One measurement, 8 runs. After your task passes the quality panel, the platform runs 4 trials per model across both models. That tier is final.
• No more provisional tier. There's no 4-run iteration check anymore, so no tier that might shift later.
• Nothing runs after acceptance. The tier your reviewer sees is the one your task keeps.
What it means for you
• At least one of the 8 runs must fail for the task to proceed. This is the same 100%-accuracy rule as before — a task every run solves gives no signal — just applied at one point instead of two.
• Keep testing locally with -k 4. It mirrors the platform measurement. Your local result is still an estimate — seeds and days move results — but there's no longer a shorter platform check that can disagree with the final one.
• Set difficulty in task.toml to your best estimate and move on. The platform's measurement is what gets recorded. A mismatch isn't a defect and reviewers won't spend time on it. (A retired tier name — easy / medium / hard — is still a problem. Use frontier / advanced / core / base.)

What hasn't changed
The tiers, the thresholds, and what makes a task hard. Base (80–100%) is still a wanted tier. 100% averaged across both models is still not accepted.

Full detail:
:link: https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/understanding-tasks/difficulty-guidelines

----------------------------
NOTE: This supersedes the earlier "Difficulty runs have changed — new two-stage model"
announcement above (the one describing 4-run in-platform iteration + 8-run post-acceptance
final). That two-stage model is retired; see this entry for the current single-measurement
model. docs/15.Difficulty Guidelines.md and the terminus3 skill have been updated to match.

----------------------------
