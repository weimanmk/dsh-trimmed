You are running exactly one synthetic AEH (Adaptive Education Harness)
acceptance session against a trimmed dsh build. Every value below is synthetic
test data. Use ONLY the six `aeh_*` tools. Do not read files, do not run shell
commands, and do not call any tool more than once.

Student reference: synthetic.student.step18
Gate mode: learn
Target retention: 0.9

Execute the six stages strictly in order A -> B -> C -> D -> E -> F. Call each
of the six tools exactly once, copying each JSON argument exactly as written.
Do not add, omit, repeat, or reorder calls. Do not invent tool results.

STAGE A - curriculum gate (门禁): call aeh_check_curriculum once with exactly
{"mode":"learn","itemId":"item.fraction.add.001","studentRef":"synthetic.student.step18"}

STAGE B - hypothesis update (假设更新): call aeh_update_hypotheses once with
exactly
{"operation":"spawn","state":{"hypotheses":[],"unknownWeight":0.4},"hypothesis":{"hypothesisId":"hyp.equiv","predictedObservableBehaviors":{"item.fraction.equiv.001":0.8,"item.fraction.compare.001":0.3},"knowledgeAssumptions":{"kc.fraction.equiv":"equivalent fractions name the same value"},"weight":0.6},"weight":0.6}
This spawns the single hypothesis hyp.equiv about fraction equivalence.

STAGE C - probe selection (探针选择): call aeh_select_probe once with exactly
{"mode":"learn","studentRef":"synthetic.student.step18","weights":{"hyp.equiv":0.6,"unknown":0.4},"candidates":[{"itemId":"item.fraction.equiv.001","predictions":{"hyp.equiv":0.8},"timeMinutes":3,"risk":0.1,"cognitiveLoad":0.25,"teachingValue":0.5},{"itemId":"item.fraction.compare.001","predictions":{"hyp.equiv":0.3},"timeMinutes":4,"risk":0.2,"cognitiveLoad":0.3,"teachingValue":0.4}]}

STAGE D - review scheduling (复习排程): call aeh_schedule_review once with
exactly
{"state":{"learnerRef":"synthetic.student.step18","memoryUnitId":"kc.fraction.equiv","stabilityDays":2,"difficulty":5,"observationCount":3,"independentSuccessCount":2,"modelFamily":"aeh.fsrs.illustrative","modelVersion":"v1"},"observations":[{"observationId":"obs.step18.trim.1","success":true,"independent":true,"kind":"attempt","occurredAt":"2026-10-27T12:05:00Z"}],"targetRetention":0.9}

STAGE E - intervention preparation (干预准备): call aeh_prepare_intervention
once with exactly
{"package":{"packageId":"pkg.equiv.hyp.equiv.001","objectiveId":"obj.fraction.equiv.hyp.equiv","trainingItemIds":["item.fraction.equiv.001"],"transferItemIds":["item.fraction.place.001"],"hintLadder":["hint.equiv.1","hint.equiv.2","hint.equiv.3"],"feedbackTemplates":{"correct":"等价分数判断正确","incorrect":"回到数轴比较等值位置"},"explanationResources":["explain.equiv.numberline"],"completionCriteria":{"independentCorrect":3,"hintFree":true},"requiredKcs":["kc.fraction.equiv"],"independentTransfer":true,"schoolMode":"learn"},"studentRef":"synthetic.student.step18","mode":"learn"}
This prepares one intervention for the hyp.equiv hypothesis. Preparation only;
it does not deliver anything.

STAGE F - report generation (报告生成): call aeh_generate_report once with
exactly
{"audience":"teacher","studentRef":"synthetic.student.step18","windowStart":"2026-10-27T00:00:00Z","windowEnd":"2026-10-28T00:00:00Z","events":[{"aggregateRef":"agg.step18.trim.1","studentRef":"synthetic.student.step18","occurredAt":"2026-10-27T12:10:00Z","kind":"attempt_aggregate","consentScope":"report:aggregate","kcId":"kc.fraction.equiv","attempts":4,"independentCorrect":3,"hintedCorrect":1,"hintsRequested":1,"minutes":10}]}

After stage F, reply with one short sentence stating that all six synthetic
stages completed.
