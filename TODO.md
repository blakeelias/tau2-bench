
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




