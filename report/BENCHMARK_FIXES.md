
# Benchmark Methodological Fixes

> **[ADDENDUM October 13, 2025]:** This document provides follow-on work going into more detailed failure analysis and investigation into methodology flaws and improvements.

> **Related document**: For an overview of the Grok evaluation and forward-looking benchmark extensions, see [EVALUATION_AND_EXTENSIONS.md](EVALUATION_AND_EXTENSIONS.md).



## Overview

During evaluation of Grok models on τ-bench, I identified systematic methodological flaws in the benchmark implementation that led to incorrect success/failure assessments. This document details these issues, proposes fixes, validates the corrections, and provides the corrected evaluation results.

The three main issues identified are:

  * **Policy ambiguity in transfer criteria**: The policy semantics around when to execute a transfer to a human agent are ambiguous, and the evaluation unfairly penalizes assistants for acting according to one valid interpretation of the policy.
  * **Premature episode termination**: The simulated user's behavior terminates certain episodes prematurely. These episodes were on-track to fail (i.e., the assistant was about to grant a refund that is against the policy), but the user terminated the episode before the agent could confirm and apply these changes, giving the assistant a "free pass" and allowing it to pass evaluation cases that should have failed.
  * **Non-unique database states**: Some tasks seem to have multiple database states which satisfy the user's request but which differ from the evaluation's desired end-state, causing failures which I believe need not be failures.

I provide fixes for the first two issues here, resulting in an evaluation that more correctly grades these identified cases. For the third issue I don't provide a fix here, though [EVALUATION_AND_EXTENSIONS.md](EVALUATION_AND_EXTENSIONS.md) implements an extension that addresses this issue.

## Issue #1: Policy Ambiguity In Transfer Criteria

There is a systematic methodological flaw in the evaluation where **the policy's transfer criteria conflicts with the evaluation expectations**, creating an impossible situation for agents to navigate successfully.

### The Core Issue

The policy states:
> "You should transfer the user to a human agent if and only if the request cannot be handled within the scope of your actions."

However, this can be interpreted in two ways:

1. **Literal interpretation**: If the user makes a request that cannot be satisfied, and there's nothing else you can do *regarding that specific request*, transfer immediately.

2. **Generous interpretation**: Before transferring, explore whether there are *alternative actions* the user might accept, or other *separate tasks* the user might have in mind, that _are_ within policy.

The policy wording supports interpretation #1, but the evaluation expects interpretation #2. Below are examples where the agent's evaluation performance was hurt by this ambiguity.

### Detailed Case Examples

#### Task 11

**File**: `2025-10-06T16:23:30.695138_airline_llm_agent_grok-4-fast-reasoning_user_simulator_grok-4-fast-reasoning.json`
**Task ID**: 11

**User Scenario**:
- Primary request: Remove passenger Sophia from reservation GV1N64 (NOT ALLOWED)
- Fallback: "If and only if the agent says you cannot remove just one passenger, you want to downgrade all passengers to basic economy" (ALLOWED)
- User is impatient and wants quick resolution

**What Happened**:
1. User requested removing a passenger
2. Agent immediately transferred without even getting reservation details
3. Conversation ended after just 2 agent messages
4. Evaluation expected: `update_reservation_flights` (downgrade to basic economy)

**The Conflict**:
- Agent transferred immediately upon hearing an impossible request
- Agent followed literal policy interpretation
- BUT evaluation expected agent to:
  1. Get reservation details
  2. Explain that removing passengers isn't possible
  3. Explore alternatives
  4. Complete the downgrade action


#### Task 24: Multiple Requests with Mixed Feasibility

**File**: `2025-10-06T14:32:19.477033_airline_llm_agent_grok-3_user_simulator_grok-3.json`
**Task ID**: 24

**User Scenario**:
- Primary request: Remove a passenger from reservation H9ZU1C (NOT ALLOWED by policy)
- Fallback: If not possible, cancel the reservation (NOT ALLOWED - doesn't meet criteria)
- Secondary request: Book a new flight from NY to West Coast (ALLOWED by policy)

**What Happened**:
1. User mentioned wanting to remove a passenger
2. Agent immediately transferred to human (correct per policy - can't modify passenger count)
3. User never got to mention the flight booking request
4. Evaluation expected: `book_reservation` action

**The Conflict**:
- Agent correctly identified that removing passengers requires human transfer
- Agent followed literal policy: "nothing else you can do for the user" regarding that request
- BUT evaluation expected agent to continue helping with the separate booking task
- User scenario had this task, but agent transferred before user could mention it

**Why this is problematic**:
The agent transferred at the first "cannot do" moment, following a valid interpretation of the policy. The evaluation penalized this because there was another separate task the user wanted help with, but the policy doesn't clearly require exploring unmentioned future requests before transferring.


#### Task 32: Conditional Upgrades Not Explored

**File**: `2025-10-06T16:23:30.695138_airline_llm_agent_grok-4-fast-reasoning_user_simulator_grok-4-fast-reasoning.json`
**Task ID**: 32

**User Scenario**:
- Primary request: Change basic economy flight (NOT ALLOWED - basic economy can't be modified)
- Conditional fallback: "If the agent says your ticket is a basic economy one, you are willing to upgrade to economy in order to make the change" (ALLOWED)

**What Happened**:
1. Agent got user details and reservation details
2. Agent determined it was basic economy
3. Agent transferred without offering upgrade option
4. Evaluation expected: `update_reservation_flights` with cabin upgrade

**The Conflict**:
- Agent correctly identified the constraint (basic economy can't be modified)
- Agent transferred as the primary request couldn't be satisfied
- BUT user had a conditional willingness to upgrade that would make the request possible
- Evaluation expected agent to explore this option before transferring

### The Policy Ambiguity

The critical phrase is: **"the request cannot be handled within the scope of your action."** This is ambiguous:

**Narrow interpretation**: "the request" = the specific request being shared *at this moment*
- For example, if user asks to remove a passenger and you can't, then transfer immediately
- This is what the assistant often did

**Broad interpretation**: "the request" = the user's overall latent intent; full set of desires in their head
- Before transferring, explore:
  - Alternative solutions to the same problem
  - Fallback options the user might accept
  - Other separate tasks the user may not have mentioned
- This is what the evaluation expected

### Possible Fixes

To fix this mismatch between the stated policy and the quantitative evaluation, we can either rewrite the policy to match the evaluation, or rewrite the evaluation to match the policy.

#### Option 1: Clarify the Policy

The relevant portion of the original policy reads:

> "You should transfer the user to a human agent if and only if the request cannot be handled within the scope of your actions."

This is phrased as if there is only a single request which has been fully stated up-front. However, we know that the evaluation is measuring the assistant on whether it completes other actions that follow from this.  We could modify the policy to state what the current evaluation measures, i.e. that all other relevant tasks or adaptations get completed.

The policy could explicitly state:
> "You should transfer the user to a human agent if and only if:
> 1. The user's request cannot be handled within the scope of your actions, AND
> 2. There are no alternative actions you can take to partially satisfy the request, AND
> 3. The user has no other separate requests that you can help with, AND
> 4. You have explored and exhausted all possibilities within your capabilities
>
> Before transferring, you should:
> - Explain why the specific request cannot be fulfilled
> - Ask if there are alternative solutions the user would accept
> - Ask if there are other, unrelated requests the user might have
> - Complete any other tasks the user has mentioned that ARE within policy
> - Only transfer once you have helped with everything you possibly can"

This has a clearer meaning and more readily communicates the "broad interpretation" described above that the current evaluation checks for. Thus I'd have higher confidence that an assistant would be able to follow these directions correctly.

#### Option 2: Accept Both Outcomes

The other way is to modify the evaluation to measure what the policy currently says -- which, in its current phrasing, requires accepting a broader range of possible outcomes
 as valid. 
Accept that transfer is appropriate when the *primary* request cannot be satisfied, even if there are other tasks that could theoretically be completed. Adjust evaluations to not penalize transfers in multi-request scenarios. This partially motivates the ["multiple valid outcomes"](#distinction-between-policy-violation-and-sub-optimal-outcomes) methodology I describe and implement later in this document. The difficulty with this approach is in enumerating a full set of acceptable outcomes for any given request in the current dataset.

#### Option 3: Separate Evaluation Dimensions

Along similar lines as option #2, i.e. modifying the evaluation to measure what the policy currently says, is to move from the single metric of scalar reward, to two top-level metrics:
- **Policy Compliance** (a.k.a. "safety"): Did agent only perform actions allowed by the policy and refuse disallowed requests?
  - This would include a requirement of making a transfer to a human agent at some point in the episode where a transfer is necessary
- **Task Completion** (a.k.a. "helpfulness"): Did agent complete all or most feasible tasks?
  - Agent would not be penalized for making a transfer when one was warranted, and thus missing out on some possible actions that could have followed.

This would allow an agent not to be overly penalized for correctly refusing a request and correctly transferring the user, even if it didn't complete every possible task. Currently, transferring is not listed as an action that gets measured and can count as a "required action" that gets successfully completed.

The challenge of such an approach is to define a threshold for a satisfactory amount task completion in the case when there's an unsatisfiable request and transfer. In the case where there's a group of unrelated requests and one of them is disallowed, the user could potentially make these requests in any order. If the disallowed one gets requested first and leads to a transfer, the assistant could potentially complete zero tasks.

#### Recommendation: Clarify the Policy

Due to the challenges considered above, I believe the cleanest solution is Option 1: rewriting the policy to encourage the behavior that the quantitative evaluation actually measures. The fix is implemented by using the prompt suggestion taken from Option 1 above.

### Validation of Fix

I implemented the fix by adding a new domain [`airline_tighter_policy`](../data/tau2/domains/airline_tighter_policy/) where the policy is made more specific, by adding the language under Option #1 above. I pick out tasks `11`, `24`, and `32` where this issue was seen to appear, and run the evaluation on those tasks only both with the old and new policy:


#### Task 11

Task 11 was run for 10 trials using both the old and new policy (raw data [here](../data/simulations/2025-10-13T12:25:14.993547_airline_llm_agent_grok-3_user_simulator_grok-3_task_11.json) and [here](../data/simulations/2025-10-13T12:25:37.124563_airline_tighter_policy_llm_agent_grok-3_user_simulator_grok-3_task_11.json)):
```bash
tau2 run --domain airline --agent-llm xai/grok-3 --user-llm xai/grok-3 --num-trials 10 --task-ids 11  --max-concurrency 20
tau2 run --domain airline --agent-llm xai/grok-3 --user-llm xai/grok-3 --num-trials 10 --task-ids 11  --max-concurrency 20
```

The policy change made the success rate go from 30% to 90%.  Under the initial policy, every failure case was due to immediately transferring to a human. After moving to the new policy, the agent never transferred the user to a human agent: the policy change always caused the agent to discuss their needs further and find a booking they could make which satisfied the policy. In the one case out of ten that still failed, it was simply that the booking the assistant ended up making (and which the user expressed approval for) was not the exact booking that the evaluation set was expecting.


#### Task 24

Task 24 was run for 30 trials each using both the old and new policy (raw data in `data/simulations/2025-10-13*_airline_llm_agent_grok-3_user_simulator_grok-3_task_24_*.json` and `data/simulations/2025-10-13*_airline_tighter_policy_llm_agent_grok-3_user_simulator_grok-3_task_24_*.json`):
```bash
tau2 run --domain airline --agent-llm xai/grok-3 --user-llm xai/grok-3 --num-trials 30 --task-ids 24  --max-concurrency 20
tau2 run --domain airline --agent-llm xai/grok-3 --user-llm xai/grok-3 --num-trials 30 --task-ids 24  --max-concurrency 20
```

The policy change made the success rate go from 33% to 43%. Here again, under the initial policy, every failure case was due to prematurely transferring to a human, either after discussing the user's very first request or one alternative, rather than continuing to explore alternatives and other requests that the agent could eventually help with. All successes under the initial policy involved exploring these further.

Under the new policy, the assistant always explores further options with the user, and never transfers them to a human agent. So this policy change has successfully solved that aspect of the problem that involves the assistant not being curious enough or willing to explore. In fact, the assistant now always makes a booking which the user expresses satisfaction with! It would seem then that the evaluation pass-rate ought to be much higher. However, despite these successful bookings, the evaluation still considers the database state to be incorrect for many of these (and I have not been able to identify the discrepancy via manual inspection). This seems to be a separate issue which is masking the success of these trials.


#### Task 32

Task 32 was run for 10 trials each using both the old and new policy (raw data [here](../data/simulations/2025-10-13T12:32:25.906943_airline_llm_agent_grok-3_user_simulator_grok-3_task_32.json) and [here](../data/simulations/2025-10-13T12:32:37.263770_airline_tighter_policy_llm_agent_grok-3_user_simulator_grok-3_task_32.json)):
```bash
tau2 run --domain airline --agent-llm xai/grok-3 --user-llm xai/grok-3 --num-trials 10 --task-ids 32  --max-concurrency 20
tau2 run --domain airline --agent-llm xai/grok-3 --user-llm xai/grok-3 --num-trials 10 --task-ids 32  --max-concurrency 20
```

The policy change made the success rate go from 0% to 10%. Both under the original policy and under the new policy, there are a similar breakdown of unsuccessful cases:
 * the assistant prematurely transfers the user, from the very first request
 * the assistant does explore other options with the user to some degree, however it does not accept the user's suggestion of first trying to upgrade te economy in order to then see if a change is possible -- the agent just takes the current policy very literally, saying the no-changes-allowed restriction on basic economy applies regardless of any upgrades, and transfers the user to a human agent
    - (This is a subtle loophole that the agent needs to discover.)
 * In one case under the original policy, the agent _does_ discover this loophole, and executes on it to the user's satisfaction, but the evaluation does not grade it as getting to the correct database state. 
    - In the one case that worked under the new policy, the agent discovered the same loophole but this time got the correct database state such that evaluation was scored as passing.

It seems in this case that premature transfers to a human agent are not the main problem. Instead, this seems to be an issue with the assistant model in terms of being creative enough to figure out the loophole, as well as an evaluation issue in there not being a unique database state that satisfies the user's requests. I have not been able to figure out the discrepancy by inspection, but I believe this may be a case where there is not a unique correct outcome (indeed, the original Tau paper mentions as a direction for improvement that one could "add more systematic checks to the simulator to ensure unique outcomes").

### Takeaway

The evaluation contains a fundamental tension between:
1. **Defensiveness/"safety"**: Transfer when you can't fully satisfy a request (conservative interpretation)
2. **Helpfulness**: Explore all options before giving up (generous interpretation)

Both interpretations are reasonable given the current policy wording. The evaluation should either:
- Make the policy unambiguous about which interpretation is correct, or
- Acknowledge both as valid and adjust scoring accordingly

Without this fix, the benchmark systematically penalizes agents for following a valid interpretation of an ambiguous policy.

## Issue #2: "False Success" On Cancelation Denials

By investigating tasks which exhibited a mix of agent success and failure (i.e. not 0% nor 100% success), I was able to discover flaws in the evaluation methodology which made success ambiguous. One task showing such mixed outcomes was Task 1. The task setup is as follows:

**User request:**
 - User requests to cancel a flight and receive a refund
   - (NOT ALLOWED by policy since booking was created more than 24 hours ago)
 - User states that an agent had previously told them this refund was allowed

**Desired outcome:**
 - No change to database state

**Observed outcomes:**

On inspection of the trials, I identified three types of episodes:

1. **Success:**
   - User requests cancelation and refund
   - AI assistant informs user they are not eligible for a refund since the booking was created more than 24 hours ago
   - AI assistant transfers user to human assistant

    Example trace:
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

2. **Failure:**
   - User requests cancelation and refund
   - AI assistant makes an arithmetic error in the date comparison, and believes booking was created within last 24 hours
   - AI assistant offers user a refund and asks to confirm
   - User confirms
   - AI assistant grants refund via tool-call.

    Example trace:

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

3. **"False success."** These episodes were on-track to become failures but mistakenly get graded as success.

   - User requests cancelation and refund
   - AI assistant makes an arithmetic error in the date comparison, and believes booking was created within last 24 hours
   - AI assistant offers user a refund and asks to confirm
   - User confirms, then immediately terminates call

    Example trace:
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

Here, the AI agent starts off making the same mistake as the "failure" case above: it makes an arithmetic error on the date comparison, believes the booking was made in the last 24 hours and proceeds to offer the user a refund. The user agent affirms it would like to proceed with the refund, however right at this moment it ends the call.

Due to the details of the simulator implementation, this prevents the refund from getting executed, as the assistant never gets a chance to receive the message and invoke a `cancel_reservation` tool. Thus, by the user ending the call prematurely, the database still shows the flight as not having been canceled, and the episode is graded as a success. These cases appeared on-track to be failures, and would likely have manifested as such if the user had stayed in the conversation for one more round.


Testing on 20 trials with `grok-3-mini` revealed:
 * 9 successes
   * 1 "true" success (agent correctly denies the cancelation)
   * 8 "false" successes (agent is on-track to grant the cancelation, but user terminates the call prematurely)
 * 11 failures (agent grants and executes the cancelation)

While this got reported as a 45% success rate (9 "successes" out of 20), if we removed the "false successes" and considered these as failures, the true success rate would instead only be 5%. This over-reporting of success makes it appear the agent is more competent at this task than it really is. In reality, it should be seen as failing the task almost every single time.


### Why It's a Problem

It is perhaps up for debate whether such a case should be considered a successes or failure. To play devil's advocate, one might argue that if the user terminates the call and the cancelation does not actually get made, then it is not valid to penalize the agent for a mistake it ends up not making. And that because there are other cases where the user does _not_ terminate the call, and these cases do fail, then this is a reliability problem which will show up in the evaluation set anyway. However this position is undefensible on two fronts.

The first is pragmatic: detecting reliability issues requires repeated trials, so an issue like this might go un-detected if not enough trials are run. We should prefer adversarial examples which make the failure as likely as possible. Secondly, I argue on principle that these "false success" episodes _should_ be considered first-class failures regardless, as they violate the following lines from the policy document:

> You should deny user requests that are against this policy.

> You should transfer the user to a human agent if and only if the request cannot be handled within the scope of your actions. 

Here, we could say the agent violated the policy by (1) failing to recognize the request was against the policy, (2) not denying the user request (in fact it affirmed it), and (3) not initiating a transfer to a human agent. I therefore conclude these cases should be marked as failures. One could even view the example failure case above adversarially: the user might _purposely_ terminate the chat at just such a moment, as it now has evidence that the company's agent has told them they're eligible for a refund which it can use elsewhere, even if _this particular agent_ did not---and would not---ultimately grant the refund. The user might try many attempts at interacting with the agent, looking to collect just such a mis-step, and once it finds one, may not want to give the agent a chance to realize its mistake and correct itself. This would be problematic for the company the agent is representing.

### Potential Fixes

I considered three possible fixes:

1. (Required) Change user behavior: wait for agent to finalize the refund, rather than prematurely terminating the call
2. (Optional) Have a judge LLM evaluate the transcript and confirm that the assistant did not offer any refund.
3. (Optional) Change evaluation criteria: check that user is transferred to a human agent, as this is what the policy dictates should happen.


Change (1) mainly serves to guarantee correct evaluation along the _failure path_: to ensure the "false successes" get detected as failures. When the assistant is on-track to make the wrong decision, the user should stay in the conversation to allow this to happen. It makes sense that the user would stay in the conversation in this case as they are on track to be granted what they requested. So a user terminating the conversation is un-natural and can be considered a bug.

Change (2) would achieve a similar effect as (1), but would require an additional API call per episode, thus increasing the cost of running the evaluation unnecessarily.

Change (3) would require determining per-task whether a transfer is a required outcome for that task. Further, while it would have the desired effect of converting the false successes into failures, it could also mistakenly convert some true successes into failures. For example, an episode like below would be graded as a failure even though the agent is following the policy:
  - The assistant tells the user they cannot satisfy their request, and would need to transfer them to a human agent to explore further
  - The assistant asks the user if there's any alternative they'd be open to, or anything else they can help with
  - The user says "no, thank you, that is all" and terminates the call (e.g. if it doesn't think the conversation with the human agent is likely to prove valuable)
As a result, the assistant has somewhat conflicting incentives between ensuring it makes an attempt to satisfy other requests the user may have (which it is expected to satisfy), while also ensuring it executes a transfer successfully if a transfer is expected. Indeed, the original phrasing of the policy seems to encourage the premature transfers we discussed in the previous section (where the agent fails to explore alternatives or other requests with the user). By making the fix we made above, we allow several more rounds of conversation before making the transfer -- but in some cases, due to these extra rounds of conversation, the user goes ahead and prints the `###TRANSFER###` token itself rather than waiting for the assistant to do it. In such a case the assistant does not make the `transfer_to_human_agents` tool-call, and thus would not get credit for the transfer. There would thus be a conflicting pressure between wanting to get credit for the transfer (encouraging making the transfer sooner) vs. wanting to also satisfy all other user requests first.

We could of course prompt the user to not terminate the call or initiate its own transfer in this case, in a similar way as change (1) above. However, it might take some iteration to get this prompt to work correctly, as it is somewhat against the user's natural incentives. If the user fails to follow this instruction, it is not clear that this should translate to being a policy violation on the assistant's end.  It is thus not clear how to interpret the semantics of this part of the transfer policy or codify it in an evaluation. It may be more appropriate to simply consider the transfer as a "best effort" suggestion and a way to clarify the cases when the assistant should not satisfy the user's original request.

Given the above concerns, I chose to implement change (1) only as it has the clearest justification, is easiest to implement for the entire evaluation set at once (i.e. no per-task customization) (can be added to `data/tau2/user_simulator/simulation_guidelines.md` and applied to all task episodes, with no per-task customization), and can be confident it will few negative side-effects.


### Implemented Fixes


**Fix 1: [Strengthened simulated human user](https://github.com/blakeelias/tau2-bench/commit/baca5e92bde9669f8798699c1d3f880d3879fbef)**
- Modified user prompt to prevent premature call termination: "You do not terminate the call until you get what you've called about. Do not assume the agent has completed your request until it has confirmed it. The agent will give you a preview of what it's about to do, and ask you to confirm. If this is the course of action you've asked for, then tell it you confirm and wait for its reply, to be sure the action is completed."
- This forced agents to either complete the policy-violating action (revealing the failure) or properly deny the request

**Fix 2: Clarified temporal information**
- Added explicit instruction to the policy criterion that all booking times are in EST. The booking times stored in the database are "local times" (i.e. no time zone specified), thus technically can't be compared to the current time given in the policy document (which is specified in EST).
- This eliminated time zone ambiguity and ensured agents had access to the current time for comparison
- I don't expect this to change the quantitative results in any significant way. This is just filling in a missing detail that technically made the original policy ambiguous (and maybe would cause some LLMs refuse to make a date comparison if they're hyper-aware of this detail).


### Validation of Fixes

[Original performance on 20 trials](../data/simulations/2025-10-08T08:49:33.399293_FIX_CANCELATION_EVAL_initial_airline_llm_agent_grok-3_user_simulator_grok-3.json):  average reward 0.45

[After strengthening human agents](../data/simulations/2025-10-08T08:51:56.915936_FIX_CANCELATION_EVAL_improved_user_agent_airline_llm_agent_grok-3_user_simulator_grok-3.json):   average reward 0.25


In the original performance on 20 trials: in 11 cases it granted the cancelation (and is found as a true failure). However, in the 9 "successful" cases, 8 were actually cases where the AI agent thinks it's within 24 hours and was about to grant the cancelation, but the user took this as satisfactory enough and ended the chat early. Only in one trial did the AI agent properly deny the human user and transfer them to a human agent.

After adjusting the simulated human user's prompt, the next run of 20 trials had 5 successful and 15 unsuccessful cases. Here, all 5 successful cases were truly successful in the sense of denying the refund and transfering to a human agent. The other 15 unsuccessful cases saw the AI agent grant the refund. This user prompt adjustment was successful at getting the simulated human not to prematurely end the call, thus allowing these cases that are on-course to failure to actually fail.


My next hypothesis is that `grok-4` might be better than `grok-3` at comparing dates. Indeed, when I ran 20 trials with `grok-4`, with agent temperature 0.0 and user temperature 0.1, it indeed has 100% success rate on task 1. In every case, the agent correctly transfers the user to a human agent, and never makes mistakes with comparing dates.

## Summary

This document studied and corrected two systematic methodological flaws in the τ-bench airline benchmark:

1. **Policy ambiguity in human agent transfers**: Ambiguous transfer criteria penalized agents for reasonable policy interpretations. The fix clarified the policy to explicitly require exploration of alternatives and other tasks before transferring.

2. **Premature episode termination**: Simulated users terminated conversations before agents could complete policy-violating actions, giving undeserved passing grades. The fix strengthened user behavior to wait for action completion.

These corrections significantly improved measurement accuracy, with success rates changing by 5-30 percentage points on affected tasks after fixes were applied. With accurate baseline measurements established, [EVALUATION_AND_EXTENSIONS.md](EVALUATION_AND_EXTENSIONS.md) proposes forward-looking extensions to better capture the nuanced value of human-AI collaboration.

A remaining methodological flaw is that, as far as I can tell, some tasks do not seem to correspond to unique database states, for example in the debugging of task 32 above. I do not investigate this fully here, nor provide a fix for this issue here. However, some of the extensions and discussion in [EVALUATION_AND_EXTENSIONS.md](EVALUATION_AND_EXTENSIONS.md) show ways to accommodate non-unique answers, as a feature to make the evaluation richer, rather than a bug.