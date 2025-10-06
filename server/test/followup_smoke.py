from server.agents.followup_agent.followup_agent import FollowUpAgent
agent = FollowUpAgent()
for test in ['Kande','Ramboda','Mirisa','Colom','Unknownland','Ella','Kandiyapara']:
    fields, missing = agent.collect(additional_info='', followup_answers={'destination': test})
    print(test, '-> fields:', fields.get('destination'), 'missing:', list(missing.keys()))
