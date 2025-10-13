
TO-DO:

 [ ] Understand how database is structured, how actions are recorded, how states are checked

 [ ] Construct vague / ill-specified preferences, which nonetheless, upon checking the available results in the database, only have one clear, valid database state that's compatible with the preferences. This database state must be reached.

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



### Evaluating fixes

tau2 run --domain airline --agent-llm xai/grok-3-mini --user-llm xai/grok-3-mini --num-trials 4 --max-concurrency 25;  git checkout addendum;  tau2 run --domain airline_tighter_policy --agent-llm xai/grok-3-mini --user-llm xai/grok-3-mini --num-trials 4 --max-concurrency 25; git add data/simulations; git commit -am "Run more simulations for testing methodology improvements."


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

