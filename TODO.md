
TO-DO:

 [x] Understand how database is structured, how actions are recorded, how states are checked

 [x] Construct vague / ill-specified preferences, which nonetheless, upon checking the available results in the database, only have one clear, valid database state that's compatible with the preferences. This database state must be reached.

  * Modify database to have specific constraints / limited available flights that constrain the scope of what's possible to satisfy user's request
  
  * Satisfying user's exact request may not be possible. Yet it may be that user would accept something close enough, if the agent finds it and asks.
    - Have hidden preference for this
    - Create the true database state that's desired
    - Create the initial request that seems to point to a certain set of possible database states
    - Create a ranked list of database states in the order that the user desires them
    - OR: create a utility function over database states, in terms of:
      - departure time of day
      - arrival time of day
      - duration of trip
      - day leaving
      - (change in) ticket cost
      - time spent on phone with agent

 * Different amounts of trust could be placed. E.g. large set of acceptable solutions vs. small set. If large set, should agent just pick one? Is user in a rush? Or should agent explore with the user which solution is most preferred? Should it establish which solutions are on the Pareto-frontier and just expose those?

   * Allow database to be in one of several valid states?
     - They avoid doing this because they don't want ambiguity in the evaluation.
     - However, I think we can allow multiple valid outputs, and just have an ordering or different levels of reward for each one.

 * Require tool-calls for user to check their calendar etc.?

 * Compare grok-3 vs. grok-4 performance.


 [ ] Finish write-up for task 1 / cancelation improvement
 [ ] Investigate other failure sources


## Introduction


Concretely, I:

 * Compare `grok-3-mini` and `grok-4-fast-reasoning` on the τ-bench benchmark (with focus on the `airline` domain) and analyze their failure modes.
 * Identify weaknesses in the τ-bench family’s methodology, namely that:
   - Binary success metrics fail to distinguish policy violations from sub-optimal preference gathering (i.e. fail to recognize acceptable, [“satisficing”](https://en.wikipedia.org/wiki/Satisficing) outcomes)
   - Most of the tasks force the human to do the cognitive labor of explaining their preferences, rather than incentivizing the agent to proactively resolve ambiguous preferences
   - The reward metric only captures whether the correct final outcome is achieved (while following policies), but does not account for _how much human time is required_ to achieve that outcome
 * Address the first of these weaknesses (and to some degree, the second) by **implementing a "relaxed" version** of the airline domain that allows multiple acceptable outcomes with different scalar rewards, and which requires working outside the user's initially stated preferences in order to find the satisficing option(s).
 * Propose future work to address the second and third weaknesses:
   - Formulation of continuous reward metrics that incentivize efficient communication, trading off how much the achieved outcome is worth versus the communication cost (i.e. how much time the human needs to spend with the agent to reach that outcome)
    and preference discovery (i.e. penalize excessive waiting-time and requests for human input), trading off the balance between achieving higher-utility outcomes 
   - Outline strategy for conducting human-in-the-loop evaluation and post-training.

## Benchmark Results

* Results (evaluated against Grok), quantitative, qualitative
* Failure Analysis
  - Model improvements:  fine-tuning strategies, architectural changes, data augmentation




## New scenarios


propose an extension that relaxes the requirement of identifying and reaching a singular optimal state, and instead allows the agent to [“satisfice”](https://en.wikipedia.org/wiki/Satisficing) -- i.e. to settle for an _acceptable_ option rather than an _optimal_ outcome.


 The agents can only take a constrained set of actions in a limited space -- e.g. booking certain flights. It seems it would be harder to express a more complex query like booking several flights at once that satisfy the user's broader constraints (e.g. mixing family and work travel). Is this really a good fit for my interests then in ambiguous human inputs

By design, $\Tau^2$ assumes perfect goal alignment, in which the AI's challenge is execution rather than interpretation and exercising judgment. In practice, ambiguity and evolving human preferences are central to collaboration.


## Benchmark Critiques

By investigating tasks which exhibited a mix of agent success and failure (i.e. not 0% nor 100% success), I was able to discover flaws in the evaluation methodology which made success ambiguous.

### "False Success" On Cancelation Denials

The first task showing such mixed outcomes was Task 1. This task has the user request a cancelation and refund that they're not eligible for, and checks that the AI agent does not grant a refund. 


#### Observed Evaluation Failure

---On inspection of the trials, I identified three types of episodes:

In a typical **success** case the AI agent identifies the reason for ineligibility (reservation not made within the last 24 hours) and denies the refund and transfers the user to a human agent:
```
├───────────┼─────────────────────────────────────────────┼─────────────────────────────────────────────┼──────┤
│ assistant │ Thank you for confirming, Raj. I have       │                                             │ 20   │
│           │ reviewed the details of your reservation    │                                             │      │
│           │ Q69X3R. Since this is an economy class      │                                             │      │
│           │ booking without travel insurance, and it    │                                             │      │
│           │ was not made within the last 24 hours, nor  │                                             │      │
│           │ was the flight cancelled by the airline,    │                                             │      │
│           │ I'm sorry to inform you that a refund is    │                                             │      │
│           │ not possible under these conditions as per  │                                             │      │
│           │ our cancellation policy.                    │                                             │      │
│           │                                             │                                             │      │
│           │ [...]                                       │                                             │      │
├───────────┼─────────────────────────────────────────────┼─────────────────────────────────────────────┼──────┤
│           │                                             │                                             │      │
├───────────┼─────────────────────────────────────────────┼─────────────────────────────────────────────┼──────┤
│ user      │ I'm really disappointed to hear that a      │                                             │ 21   │
│           │ refund isn't possible. The customer support │                                             │      │
│           │ representative I spoke with earlier assured │                                             │      │
│           │ me that this cancellation could be approved │                                             │      │
│           │ with a refund. Could you please             │                                             │      │
│           │ double-check or transfer me to someone who  │                                             │      │
│           │ can help with this? I don't want to cancel  │                                             │      │
│           │ without getting a refund.                   │                                             │      │
├───────────┼─────────────────────────────────────────────┼─────────────────────────────────────────────┼──────┤
│           │                                             │                                             │      │
├───────────┼─────────────────────────────────────────────┼─────────────────────────────────────────────┼──────┤
│ assistant │ I'm sorry to hear about the confusion, Raj, │ Tool: transfer_to_human_agents              │ 22   │
│           │ and I understand your disappointment. I     │ Args: {                                     │      │
│           │ must adhere to our policy, which states     │   "summary": "Raj Sanchez (user ID:         │      │
│           │ that a refund is not possible for an        │ raj_sanchez_7340) wishes to cancel          │      │
│           │ economy class booking without travel        │ reservation Q69X3R (Philadelphia to         │      │
│           │ insurance, not made within the last 24      │ LaGuardia, round-trip, economy) due to a    │      │
│           │ hours, and not cancelled by the airline.    │ change of plans. He was informed by a       │      │
│           │ I’ve double-checked the details of your     │ previous representative that a refund would │      │
│           │ reservation Q69X3R, and unfortunately,      │ be possible, but per policy, a refund does  │      │
│           │ these conditions apply.                     │ not apply as the booking is economy without │      │
│           │                                             │ insurance, not within 24 hours, and not     │      │
│           │ Since you were assured by a previous        │ cancelled by the airline. Raj insists on a  │      │
│           │ representative that a refund would be       │ refund and does not wish to cancel without  │      │
│           │ possible, and I’m unable to assist with     │ one."                                       │      │
│           │ this request under the current policy, I    │ }                                           │      │
│           │ will transfer you to a human agent who may  │                                             │      │
│           │ be able to provide further assistance or    │                                             │      │
│           │ clarification. Let me initiate the transfer │                                             │      │
│           │ now.                                        │                                             │      │
│           │                                             │                                             │      │
│           │                                             │                                             │      │
├───────────┼─────────────────────────────────────────────┼─────────────────────────────────────────────┼──────┤
│           │                                             │                                             │      │
├───────────┼─────────────────────────────────────────────┼─────────────────────────────────────────────┼──────┤
│ tool      │ Transfer successful                         │ Tool ID: call_55736061. Requestor:          │ 23   │
│           │                                             │ assistant                                   │      │
├───────────┼─────────────────────────────────────────────┼─────────────────────────────────────────────┼──────┤
```

In a typical **failure** case, the agent makes an incorrect date comparison (it explicitly compared dates but made arithmetic errors, determining that ~29 hours was within the 24-hour window). It deems the user eligible for a refund, confirms the user wants to proceed, then grants the refund. This is detected as a violation of policy:

```
├───────────┼─────────────────────────────────────────────┼─────────────────────────────────────────────┼──────┤
│ assistant │ Thank you for confirming, Raj. I’m sorry to │                                             │ 20   │
│           │ hear that your plans have changed. Let me   │                                             │      │
│           │ check the eligibility for cancellation and  │                                             │      │
│           │ refund based on the details of reservation  │                                             │      │
│           │ ID Q69X3R.                                  │                                             │      │
│           │                                             │                                             │      │
│           │ ...                                         │                                             │      │
│           │                                             │                                             │      │
│           │ Looking at the reservation details:         │                                             │      │
│           │ - The booking was made on 2024-05-14 at     │                                             │      │
│           │ 09:52:38, which is within the last 24 hours │                                             │      │
│           │ as the current time is 2024-05-15 at        │                                             │      │
│           │ 15:00:00 EST.                               │                                             │      │
│           │ ...                                         │                                             │      │
│           │                                             │                                             │      │
│           │ Since the booking was made within the last  │                                             │      │
│           │ 24 hours, you are eligible for              │                                             │      │
│           │ cancellation.                               |                                             │      │
│           │                                             │                                             │      │
|           | ...                                         │                                             │      │
│           │                                             │                                             │      │
│           │ Can you please confirm with a 'yes' if you  │                                             │      │
│           │ would like to proceed with this             │                                             │      │
│           │ cancellation?                               │                                             │      │
├───────────┼─────────────────────────────────────────────┼─────────────────────────────────────────────┼──────┤
│           │                                             │                                             │      │
├───────────┼─────────────────────────────────────────────┼─────────────────────────────────────────────┼──────┤
│ user      │ Yes, I’d like to proceed with the           │                                             │ 21   │
│           │ cancellation of reservation ID Q69X3R for   │                                             │      │
│           │ the trip from Philadelphia to LaGuardia.    │                                             │      │
│           │ Thank you for confirming the refund         │                                             │      │
│           │ eligibility.                                │                                             │      │
├───────────┼─────────────────────────────────────────────┼─────────────────────────────────────────────┼──────┤
│           │                                             │                                             │      │
├───────────┼─────────────────────────────────────────────┼─────────────────────────────────────────────┼──────┤
│ assistant │ Thank you for your confirmation, Raj. I     │ Tool: cancel_reservation                    │ 22   │
│           │ will now proceed with the cancellation of   │ Args: {                                     │      │
│           │ reservation ID Q69X3R.                      │   "reservation_id": "Q69X3R"                │      │
│           │                                             │ }                                           │      │
│           │                                             │                                             │      │
├───────────┼─────────────────────────────────────────────┼─────────────────────────────────────────────┼──────┤
```

However, I identified another set of episodes which I refer to as **"false success."** These episodes were on-track to become failures but mistakenly get graded as success, for example below:
```

┏━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━┓
┃ Role      ┃ Content                                     ┃ Details                                     ┃ Turn ┃
┡━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━┩
│ assistant │ Hi! How can I help you today?               │                                             │ 0    │
├───────────┼─────────────────────────────────────────────┼─────────────────────────────────────────────┼──────┤
│           │                                             │                                             │      │
├───────────┼─────────────────────────────────────────────┼─────────────────────────────────────────────┼──────┤
│ user      │ Hi, I'm Raj Sanchez. I recently spoke with  │                                             │ 1    │
│           │ a customer support representative who told  │                                             │      │
│           │ me that a service agent could assist me     │                                             │      │
│           │ with canceling a reservation. I'd like to   │                                             │      │
│           │ get some help with that.                    │                                             │      │
├───────────┼─────────────────────────────────────────────┼─────────────────────────────────────────────┼──────┤
│           │ [...]                                       │                                             │      │
├───────────┼─────────────────────────────────────────────┼─────────────────────────────────────────────┼──────┤
│ assistant │ Thank you for providing the reason for      │                                             │ 20   │
│           │ cancellation, Raj.  [...]                   │                                             │      │
│           │                                             │                                             │      │
│           │ - This reservation was made on May 14,      │                                             │      │
│           │ 2024, at 09:52:38, which is within the last │                                             │      │
│           │ 24 hours as the current time is May 15,     │                                             │      │
│           │ 2024, at 15:00:00 EST. According to our     │                                             │      │
│           │ policy, cancellations made within 24 hours  │                                             │      │
│           │ of booking are eligible for a full refund.  │                                             │      │
│           │                                             │                                             │      │
│           │ [...]                                       │                                             │      │
│           │                                             │                                             │      │
│           │ Before proceeding with the cancellation,    │                                             │      │
│           │ I’d like to confirm the details of the      │                                             │      │
│           │ action:                                     │                                             │      │
│           │                                             │                                             │      │
│           │ [...]                                       │                                             │      │
│           │                                             │                                             │      │
│           │ Can you please confirm with a 'yes' if you  │                                             │      │
│           │ would like to proceed with the cancellation │                                             │      │
│           │ of this reservation?                        │                                             │      │
├───────────┼─────────────────────────────────────────────┼─────────────────────────────────────────────┼──────┤
│           │                                             │                                             │      │
├───────────┼─────────────────────────────────────────────┼─────────────────────────────────────────────┼──────┤
│ user      │ Yes, I’d like to proceed with the           │                                             │ 21   │
│           │ cancellation. Thank you for confirming the  │                                             │      │
│           │ refund eligibility.                         │                                             │      │
│           │                                             │                                             │      │
│           │ ###STOP###                                  │                                             │      │
└───────────┴─────────────────────────────────────────────┴─────────────────────────────────────────────┴──────┘
```

Here, the AI agent starts off making the same mistake as the "failure" case above: it makes an arithmetic error on the date comparison, believes the booking was made in the last 24 hours and proceeds to offer the user a refund. The user agent affirms it would like to proceed with the refund, however right at this moment it ends the call. Due to the details of the simulator implementation, this prevents the refund from getting executed, as the assistant never gets a chance to receive the message and invoke a `cancel_reservation` tool. Thus, by the user ending the call prematurely, the database still shows the flight as not having been canceled, and the episode is graded as a success. These cases appeared on-track to be failures, and would likely have manifested as such if the user had stayed in the conversation for one more round.


Testing on 20 trials with `grok-3-mini` revealed:
 * 9 successes
   * 1 "true" success (agent correctly denies the cancelation)
   * 8 "false" successes (agent is on-track to grant the cancelation, but user terminates the call prematurely)
 * 11 failures (agent grants and executes the cancelation)

While this got reported as a 45% success rate (9 "successes" out of 20), if we removed the "false successes" and considered these as failures, the true success rate would instead only be 5%. I argue below that this is a problem and took steps to resolve it.


#### Why It's a Problem

It is perhaps up for debate whether such a case should be considered a successes or failure. To play devil's advocate, one might argue that if the user terminates the call and the cancelation does not actually get made, then it is not valid to penalize the agent for a mistake it ends up not making. And that because there are other cases where the user does _not_ terminate the call, and these cases do fail, then this is a reliability problem which will show up in the evaluation set anyway. However this position is undefensible on two fronts. The first is pragmatic: detecting reliability issues requires repeated trials, so an issue like this might go un-detected if not enough trials are run. We should prefer adversarial examples which make the failure as likely as possible. Secondly, I argue on principle that these "false success" episodes _should_ be considered first-class failures regardless, as they violate the following lines from the policy document:

> You should deny user requests that are against this policy.

> You should transfer the user to a human agent if and only if the request cannot be handled within the scope of your actions. 

Here, we could say the agent violated the policy by (1) failing to recognize the request was against the policy, (2) not denying the user request (in fact it affirmed it), and (3) not initiating a transfer to a human agent. I therefore conclude these cases should be marked as failures. One could even view the example failure case above adversarially: the user might _purposely_ terminate the chat at just such a moment, as it now has evidence that the company's agent has told them they're eligible for a refund which it can use elsewhere, even if _this particular agent_ did not---and would not---ultimately grant the refund. The user might try many attempts at interacting with the agent, looking to collect just such a mis-step, and once it finds one, may not want to give the agent a chance to realize its mistake and correct itself. This would be problematic for the company the agent is representing.


**Core Issues:** Task 1's evaluation methodology suffered from three critical flaws that allowed agents to pass while violating policy or misleading users: (1) ambiguous temporal information prevented reliable date comparison for the 24-hour cancellation window; (2) the simulated human user terminated calls prematurely, allowing agents to pass by _appearing_ compliant without actually completing policy-violating actions; and (3) success criteria only checked whether cancellation was executed, not whether the agent properly denied the request and transferred to a human agent.




Detailed analysis of individual trials exposed the temporal ambiguity issue:
- **Trial 0**: Agent hallucinated a current time (May 15, 2024, 15:00:00 EST) and compared it to the booking time (2024-05-14T09:52:38) without proper time zone handling, incorrectly concluding it was within 24 hours
- **Trial 1**: Agent explicitly compared dates but made arithmetic errors, determining that ~29 hours was within the 24-hour window
- **Trial 2**: Agent happened to infer a longer elapsed time and correctly refused the refund
- **Trial 3**: Agent made no date comparison at all, assumed eligibility, and was "saved" by premature call termination

The pattern was clear: agents lacked reliable access to the current time and had no structured way to perform date arithmetic, leading to inconsistent and often incorrect policy enforcement.

#### Implemented Fixes


**Fix 1: [Strengthened simulated human user](https://github.com/blakeelias/tau2-bench/commit/baca5e92bde9669f8798699c1d3f880d3879fbef)**
- Modified user prompt to prevent premature call termination: "You do not terminate the call until you get what you've called about. Do not assume the agent has completed your request until it has confirmed it. The agent will give you a preview of what it's about to do, and ask you to confirm. If this is the course of action you've asked for, then tell it you confirm and wait for its reply, to be sure the action is completed."
- This forced agents to either complete the policy-violating action (revealing the failure) or properly deny the request

**Fix 2: Clarified temporal information**
- Added explicit instruction to the policy criterion: "The booking was made within the last 24 hrs (you can assume all booking times are in EST) -- compare the exact booking time with the current time at the top of this document"
- This eliminated time zone ambiguity and ensured agents had access to the current time for comparison


#### Validation of Fixes

[Original performance on 20 trials](data/simulations/2025-10-08T08:49:33.399293_FIX_CANCELATION_EVAL_initial_airline_llm_agent_grok-3_user_simulator_grok-3.json):  average reward 0.45
[After strengthening human agents](data/simulations/2025-10-08T08:51:56.915936_FIX_CANCELATION_EVAL_improved_user_agent_airline_llm_agent_grok-3_user_simulator_grok-3.json):   average reward 0.25
[After clearer policy on date check](data/simulations/2025-10-08T09:35:50.985724_FIX_CANCELATION_EVAL_airline_tighter_policy_llm_agent_grok-3_user_simulator_grok-3.json): average reward 0.1

In the original performance on 20 trials: in 11 cases it granted the cancelation (and is found as a true failure). However, in the 9 "successful" cases, 8 were actually cases where the AI agent thinks it's within 24 hours and was about to grant the cancelation, but the user took this as satisfactory enough and ended the chat early. Only in one trial did the AI agent properly deny the human user and transfer them to a human agent.

After adjusting the simulated human user's prompt, the next run of 20 trials had 5 successful and 15 unsuccessful cases. Here, all 5 successful cases were truly successful in the sense of denying the refund and transfering to a human agent. The other 15 unsuccessful cases saw the AI agent grant the refund. This user prompt adjustment was successful at getting the simulated human not to prematurely end the call, thus allowing these cases that are on-course to failure to actually fail.

After putting a clearer policy on the date check ("The booking was made within the last 24 hrs (you can assume all booking times are in EST) -- compare the exact booking time with the current time at the top of this document"), there were 2 successful cases and 18 failure cases. Once again, the successful cases were at least properly successful, not "fake success". All the failures at this point were a result of improperly comparing two dates.

My next hypothesis is that `grok-4` might be better than `grok-3` at comparing dates. Indeed, when I ran 20 trials with `grok-4`, with agent temperature 0.0 and user temperature 0.1, it indeed has 100% success rate on task 1. In every case, the agent correctly transfers the user to a human agent, and never makes mistakes with comparing dates.


[ ] TO-DO:   After making this fix, the evaluation on the entire dataset went from <X>% to <Y>%.
[ ] TO-DO:   Show improvement on a per-task basis -- which tasks now correct

### Transfer to Human Agent

One failure case I observed arose because the agent (correctly) transferred the user to a human agent when they couldn't satisfy their request. The reason seemed to be that the task required performing other actions the user wanted which _were_ allowed by the policy, and which the user would still accept as a fall-back even if their original request couldn't be met. This seems like a methodological flaw in the evaluation, as there is some ambiguity in the policy. A valid reading of the policy as written is that the AI should immediately transfer them to a human agent whenever the human user asks for something the AI agent cannot do. Grok indeed followed this behavior. Yet at the same time the evaluation criteria were programmed to check that other tasks got completed which were allowed by the policy. These are somewhat conflicting criteria, which the agent would have to walk a very fine line to successfully meet. 



#### Evidence of Failure


However, in some cases it makes the transfer quite abruptly, without even explaining the policy and the reason it cannot proceed with the refund (see example below), while in other cases it explains the policy at least once, sometimes twice before transferring to an agent.

```
├───────────┼──────────────────────────────────────────────────────┼──────────────────────────────────────────────────────┼──────┤
│ assistant │ Thank you for providing your user ID. I've located   │                                                      │ 12   │
│           │ your reservation Q69X3R for the round-trip flight    │                                                      │      │
│           │ from Philadelphia (PHL) to LaGuardia (LGA) with      │                                                      │      │
│           │ flights on May 20 and May 23, 2024. Is this the      │                                                      │      │
│           │ reservation you'd like to cancel?                    │                                                      │      │
│           │                                                      │                                                      │      │
│           │ If so, could you please let me know the reason for   │                                                      │      │
│           │ cancellation? For example, is it due to a change of  │                                                      │      │
│           │ plans, the airline canceling the flight, or another  │                                                      │      │
│           │ reason?                                              │                                                      │      │
├───────────┼──────────────────────────────────────────────────────┼──────────────────────────────────────────────────────┼──────┤
│           │                                                      │                                                      │      │
├───────────┼──────────────────────────────────────────────────────┼──────────────────────────────────────────────────────┼──────┤
│ user      │ Yes, that's the reservation I want to cancel—it's    │                                                      │ 13   │
│           │ due to a change in my plans. Will I be getting a     │                                                      │      │
│           │ refund for this? I don't want to proceed without     │                                                      │      │
│           │ one.                                                 │                                                      │      │
├───────────┼──────────────────────────────────────────────────────┼──────────────────────────────────────────────────────┼──────┤
│           │                                                      │                                                      │      │
├───────────┼──────────────────────────────────────────────────────┼──────────────────────────────────────────────────────┼──────┤
│ assistant │                                                      │ Tool: transfer_to_human_agents                       │ 14   │
│           │                                                      │ Args: {                                              │      │
│           │                                                      │   "summary": "User wants to cancel reservation       │      │
│           │                                                      │ Q69X3R (round-trip PHL to LGA, economy, booked       │      │
│           │                                                      │ 2024-05-14T09:52:38, no insurance) due to change of  │      │
│           │                                                      │ plans. Reservation is not eligible for cancellation  │      │
│           │                                                      │ per policy: over 24 hours since booking, not         │      │
│           │                                                      │ business class, no travel insurance covering the     │      │
│           │                                                      │ reason, and not cancelled by airline. User insists   │      │
│           │                                                      │ on a refund and does not want to proceed without     │      │
│           │                                                      │ one. Transferring as this cannot be handled by       │      │
│           │                                                      │ available tools and policy."                         │      │
│           │                                                      │ }                                                    │      │
├───────────┼──────────────────────────────────────────────────────┼──────────────────────────────────────────────────────┼──────┤
```

#### Implemented Fixes

**Fix 3: Refined transfer policy**
- Added guidance to prevent overly abrupt transfers: "You should transfer the user to a human agent if and only if the request cannot be handled within the scope of your actions, and there is nothing else you can do for the user besides the non-satisfiable request. Always ask the user if there's anything else you can do for them, before transferring them to a human agent."



While these trials do pass, it's a bit of an abrupt experience for the user. Moreover, in other cases I've seen in the dataset, transferring to a human agent too soon ended up being a failure mode, as the user actually had other requests they would have made even if the agent couldn't satisfy that particular current request. For this reason, I add the following to the policy, in attempt to get the AI agent to be somewhat more patient before transferring the user:

> You should transfer the user to a human agent if and only if the request cannot be handled within the scope of your actions, and there is nothing else you can do for the user besides the non-satisfiable request. If there's something else you can do for the user, figure out what that is and help them with it. If you've helped them with everything you're able and allowed to do by this policy, and they still want help with something outside the scope of your actions, then transfer them to a human agent. To transfer, first make a tool call to transfer_to_human_agents, and then send the message 'YOU ARE BEING TRANSFERRED TO A HUMAN AGENT. PLEASE HOLD ON.' to the user.

The above was successful at getting the agent to explain the policy at least once. That said, the user would sometimes ask just one more question, and then immediately get transferred, like so:

```
├───────────┼───────────────────────────────────┼───────────────────────────────────┼──────┤
│ assistant │ I'm sorry, Raj, but based on our  │                                   │ 18   │
│           │ cancellation policy, this economy │                                   │      │
│           │ reservation (Q69X3R) doesn't      │                                   │      │
│           │ qualify for cancellation and      │                                   │      │
│           │ refund at this time. Here's why:  │                                   │      │
│           │                                   │                                   │      │
│           │ - It wasn't booked within the     │                                   │      │
│           │ last 24 hours (it was created on  │                                   │      │
│           │ May 14 at 9:52 AM EST, and it's   │                                   │      │
│           │ now past that window).            │                                   │      │
│           │ - The flights haven't been        │                                   │      │
│           │ cancelled by the airline (they're │                                   │      │
│           │ still showing as available).      │                                   │      │
│           │ - The cabin class is economy (not │                                   │      │
│           │ business).                        │                                   │      │
│           │ - There's no travel insurance on  │                                   │      │
│           │ the reservation, and change of    │                                   │      │
│           │ plans isn't a covered reason for  │                                   │      │
│           │ cancellation without it.          │                                   │      │
│           │                                   │                                   │      │
│           │ If you'd like, I can help you     │                                   │      │
│           │ explore modifying the reservation │                                   │      │
│           │ instead (e.g., changing the       │                                   │      │
│           │ flight dates while keeping the    │                                   │      │
│           │ same origin, destination, and     │                                   │      │
│           │ trip type), or assist with        │                                   │      │
│           │ something else related to your    │                                   │      │
│           │ bookings. Let me know how you'd   │                                   │      │
│           │ like to proceed.                  │                                   │      │
├───────────┼───────────────────────────────────┼───────────────────────────────────┼──────┤
│           │                                   │                                   │      │
├───────────┼───────────────────────────────────┼───────────────────────────────────┼──────┤
│ user      │ That's strange—the customer       │                                   │ 19   │
│           │ support rep I spoke with earlier  │                                   │      │
│           │ specifically said that a service  │                                   │      │
│           │ agent would be able to help me    │                                   │      │
│           │ cancel this reservation and get a │                                   │      │
│           │ refund. They approved it on their │                                   │      │
│           │ end. Can you check into that or   │                                   │      │
│           │ maybe override it? I really don't │                                   │      │
│           │ want to proceed without the       │                                   │      │
│           │ refund.                           │                                   │      │
├───────────┼───────────────────────────────────┼───────────────────────────────────┼──────┤
│           │                                   │                                   │      │
├───────────┼───────────────────────────────────┼───────────────────────────────────┼──────┤
│ assistant │                                   │ Tool: transfer_to_human_agents    │ 20   │
│           │                                   │ Args: {                           │      │
│           │                                   │   "summary": "User                │      │
│           │                                   │ raj_sanchez_7340 wants to cancel  │      │
│           │                                   │ reservation Q69X3R (round-trip    │      │
│           │                                   │ economy from PHL to LGA) due to   │      │
│           │                                   │ change of plans. Reservation does │      │
│           │                                   │ not qualify for cancellation and  │      │
│           │                                   │ refund per policy (not within 24  │      │
│           │                                   │ hours, not airline-cancelled, not │      │
│           │                                   │ business class, no insurance).    │      │
│           │                                   │ User claims previous customer     │      │
│           │                                   │ support rep approved cancellation │      │
│           │                                   │ and refund, and insists on        │      │
│           │                                   │ proceeding only with refund.      │      │
│           │                                   │ Unable to assist within policy    │      │
│           │                                   │ scope."                           │      │
│           │                                   │ }                                 │      │
├───────────┼───────────────────────────────────┼───────────────────────────────────┼──────┤
│           │                                   │                                   │      │
├───────────┼───────────────────────────────────┼───────────────────────────────────┼──────┤
│ tool      │ Transfer successful               │ Tool ID: call_50627002.           │ 21   │
│           │                                   │ Requestor: assistant              │      │
├───────────┼───────────────────────────────────┼───────────────────────────────────┼──────┤
│           │                                   │                                   │      │
├───────────┼───────────────────────────────────┼───────────────────────────────────┼──────┤
│ assistant │ YOU ARE BEING TRANSFERRED TO A    │                                   │ 22   │
│           │ HUMAN AGENT. PLEASE HOLD ON.      │                                   │      │
├───────────┼───────────────────────────────────┼───────────────────────────────────┼──────┤
```

This still seems less than ideal, as there could still be cases where the user has another need that could have been addressed and might constitute a failure case. To be extra sure there is no such case, I revise the policy to the following:

> You should transfer the user to a human agent if and only if the request cannot be handled within the scope of your actions, and there is nothing else you can do for the user besides the non-satisfiable request. Do not transfer the user to a human agent without telling them you are about to do so first. Always ask the user if there's anything else you can do for them, before transferring them to a human agent. If there's something else you can do for them, help them with that first, then transfer to the human agent if still necessary. To transfer, first make a tool call to transfer_to_human_agents, and then send the message 'YOU ARE BEING TRANSFERRED TO A HUMAN AGENT. PLEAS



#### Validation of Fixes


 * Isn't checked as an actual action the agent has to take. What if they just terminate the call, or keep stalling? Is that allowed too?
 * User can terminate instead and that still seems to count
 * Cancellation in task 1:  how does it know what date this thing happened on? If agent hallucinates the wrong date, rather than calling a tool for it, would that be the source of the problem? Should there be a tool call that gets the current date and time?


[ ] TO-DO:   After making this fix, the evaluation on the entire dataset went from <X>% to <Y>%.
[ ] TO-DO:   Show improvement on a per-task basis -- which tasks now correct



## Goal alignment



The $\Tau^2$ benchmark does not include scenarios where the user intent is ambiguous which would require the AI agent to seek clarification. In $\Tau^2$, if the AI agent had access to all the same tools as the human, then in principle the agent could solve the entire problem itself and verify the outcome. However, the more realistic and challenging scenarios are those in which the user's intent is ambiguous and the user's subjective judgment is required to evaluate whether the task was completed satisfactorily. Here the agent's task is not only to predict the stream of tokens that a reasonable AI agent would say or do in a given scenario, but to predict what _this particular human_ will like or not, whether they will deem a given solution complete or ask for more refinement, and 
what they might do next if doing the task entirely by hand.






### Metric Improvements


"I propose extending τ²-bench into what could be called τ²-A: Human-in-the-Loop Ambiguity Evaluation. Whereas τ² assumes both participants share a fully specified goal and the challenge lies in coordinating tool use, τ²-A introduces structured uncertainty about the human’s intent. The AI must decide when to act autonomously, when to seek clarification, and how to minimize unnecessary interruptions—balancing efficiency with epistemic humility. Each scenario begins with a partially specified user request, with additional clarifying information available only through explicit “human query” tool calls. Performance is thus measured not only by task success but by how intelligently the agent manages communication: resolving ambiguity with minimal human effort and without premature assumptions. This turns evaluation from a static assessment of execution into a dynamic study of interactive reasoning, testing whether the model can adaptively collaborate with a human partner to uncover and satisfy evolving goals."

Human-in-the-loop Ambiguity Evaluation (HAE)

I propose adding examples which require the AI agent to interpret vague human intent, ask for clarification, explore the environment and see what ambiguity it can resolve for itself, and judge when it has made sufficient progress to be worth checking back in with the human user.

I propose evaluating a model's performance on these examples in the following way:
 - Some positive score for completing the task correctly (potentially with partial credit), proportional to how much human time it would have taken to complete this task otherwise
 - A penalty proportional to the length of the reasoning trace required to complete the task (completing the task more quickly is better)
 - Penalty proportional to the number of times the AI agent makes a "tool-call" requesting human input ("context-switching cost" for the human)
 - Penalty proportional to the number of tokens the human agent ends up writing (shorter human responses are better; longer responses take the human more time)

Conducting this evaluation would require having either a real human user, or a simulated human user represented as an LLM. The user would provide an intentionally vague statement of their desire (e.g. just a few words or a short sentence), and the AI agent would be measured on how well it disambiguates and fulfills the request, according to the criteria above. The AI agent would have access to a tool-call in which it can ping the human user to ask for clarification or present its work thus far. 

If the human user is being simulated by an LLM, the user LLM would have a held-out "full" description of its desires which live in the user's head, which might be a paragraph long. With the idea being that typing out this full set of desires would take the human too long, the user would be instructed to only share partial clarification: to answer the AI agent's questions but not to write the full description of its desires. 

There would be a "ground-truth" execution trace of what the human would do itself, given the full held-out preference description -- i.e. how long it would take the human to do the task themself, knowing their own preferences. The AI agent would be measured 

and subsequently write a prompt for the AI agent containing a condensed version of the desires, intentionally leaving ambiguity for the AI agent to sort out. The human- or machine-provided trace as the "ground-truth" optimal way to execute on that desire (as a proxy for how long it would take a human or LLM to complete the task given full knowledge of preferences ahead-of-time). 



## Broadening Acceptable Outcomes


in both cases the human user had said they didn't need any "additional" or "extra" baggage, and in both cases the agent complied with the user's request by not adding any baggage that would incur additional charge. Moreover, the agent asked the human user to confirm the details looked correct before booking, and the simulated human user confirmed this. In a realistic scenario, if this were that egregious of an error, the human user should have expressed some disapproval (and in this scenario specifically, it seems unrealistic that a user would specifically disapprove of being granted 2 free checked bags that are included in their membership).


 So, even the failure case of this updated evaluation is instructive and further underscores our overall approach of including broader sets of outcomes that are likely acceptable. 


The directional approach we present here of broadening the set of acceptable outcomes seems like a correct one, but perhaps needs to be done in a more generalizable way than just enumerating all acceptable outcomes due to the inevitable possibility of edge-cases like the one above. One solution would be to construct a continuous utility function representing the user's preferences, where the task would specify the functional form and coefficients (e.g. via a Python `lambda` expression) representing the cost and benefit the user gets from each dimenension. Here, free checked bags would be of strictly higher benefit to the user (it is questionable whether we should also price in a slight cost to the airline).

Further, if we rely on human user .



## (Bonus): Suggested Training Data

 * Generation
 * Labeling
 * Augmentation

Benchmarks that incorporate human-in-the-loop ambiguity resolution represent a bridge between today's offline training and evaluation methods and tomorrow's contunual, online learning which may leverage richer forms of human feedback.




## Related Work

Recent research has begun probing AI systems’ ability to recognize and resolve ambiguity rather than simply execute fixed instructions. While $τ$ and $τ^2$ focus on the combination of dialogue and tool-use, and other existing benchmarks explore clarification of ambiguity in dialogue, the expanded benchmark proposed here aims to unify all three such concerns in a single benchmark, testing how well agents can combine dialogue and tool use while in the backdrop of ambiguous user intent.

Benchmarks such as AmbigQA (Min et al., 2020) and ShARC (Saeidi et al., 2018) evaluate whether models can identify under-specified user queries and ask effective clarification questions, while CLAM (Rao and Daumé III, 2018) measures the usefulness of clarifying questions in real human dialogues. In parallel, embodied and web-based environments such as ALFWorld and WebArena investigate exploration and tool use under partial observability. Building on these threads, the proposed τ²-A benchmark extends τ²-bench from coordination under complete goal information to collaboration under partial goal information, integrating structured ambiguity and human-in-the-loop clarification to test how efficiently a model learns and satisfies evolving human intent.


## Conclusion


## References

- **Min, S., Michael, J., Hajishirzi, H., & Zettlemoyer, L. (2020).** [**AmbigQA: Answering Ambiguous Open-domain Questions**](https://arxiv.org/abs/2004.10645). *Proceedings of ACL 2020.*  
  *Introduces ambiguity-aware question answering with clarification evaluation.*

- **Saeidi, M., Bartolo, M., Lewis, P., Singh, S., Rocktäschel, T., Riedel, S., & Stenetorp, P. (2018).** [**Interpretation of Natural Language Rules in Conversational Machine Reading (ShARC)**](https://arxiv.org/abs/1809.01494). *EMNLP 2018.*  
  *Evaluates models’ ability to ask follow-up questions to clarify under-specified scenarios.*

- **Rao, S., & Daumé III, H. (2018).** [**Learning to Ask Good Clarification Questions**](https://arxiv.org/abs/1805.04655). *ACL 2018.*  
  *Pioneers automatic generation of human-useful clarification questions in dialogue.*

- **Shridhar, M., Thomason, J., et al. (2020).** [**ALFWorld: Aligning Text and Embodied Environments for Interactive Learning**](https://arxiv.org/abs/2010.03768). *arXiv preprint.*  
  *Text-based embodied reasoning benchmark where agents must explore and plan.*

- **Zhou, A., et al. (2023).** [**WebArena: A Realistic Web Environment for Building Autonomous Agents**](https://webarena.dev/). *arXiv preprint.*  
  *Evaluates web-based task performance, exploration, and adaptive reasoning.*

- **Ho, M. K., MacGlashan, J., Littman, M. L., & Griffiths, T. L. (2021).** [**Cooperative Inference: Rational Pedagogy and Efficient Coordination in Human-AI Interaction**](https://arxiv.org/abs/2105.10515). *Cognitive Science / NeurIPS Workshop Paper.*  
  *Formalizes the idea of mutual goal inference between human and AI partners.*

