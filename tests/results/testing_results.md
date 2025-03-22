  "id": "2",
  "text": "Considering your...
INFO     ai_service.api.services.openai.service:service.py:460 OpenAI API call successful for astrological_question_generation
INFO     ai_service.api.services.session_service:session_service.py:139 Session persisted to file: 87d3ae21-7702-4ad9-93e6-2eb8bf6a129a
INFO     ai_service.api.services.session_service:session_service.py:292 Session updated: 87d3ae21-7702-4ad9-93e6-2eb8bf6a129a
INFO     tests.integration.test_sequence_flow_real:test_sequence_flow_real.py:264 Successfully saved data to /app/tests/test_data_source/test_db.json
INFO     tests.integration.test_sequence_flow_real:test_sequence_flow_real.py:291 Updated question_answers/87d3ae21-7702-4ad9-93e6-2eb8bf6a129a_e47b8f2c-1 in test database
INFO     tests.integration.test_sequence_flow_real:test_sequence_flow_real.py:957 Question progression: physical_traits -> personality_traits
INFO     tests.integration.test_sequence_flow_real:test_sequence_flow_real.py:876 Processing question 2: Considering your typical emotional responses and interpersonal interactions, which of the following descriptions resonates most closely with your personality? (Category: personality_traits)
INFO     ai_service.api.services.openai.service:service.py:58 API key configured (length: 164)
INFO     ai_service.api.services.openai.service:service.py:69 Initializing direct API client
INFO     ai_service.api.services.openai.service:service.py:107 Registered client with test tracker
INFO     ai_service.api.services.openai.service:service.py:110 Initialized direct API client for OpenAI with Timeout(connect=10.0, read=90.0, write=10.0, pool=10.0)
INFO     ai_service.api.services.openai.service:service.py:148 OpenAI service initialized with model: gpt-4-turbo-preview
INFO     ai_service.api.services.openai.service:service.py:304 Sending request to OpenAI API (model: gpt-4-turbo-preview, task: questionnaire)
INFO     httpx:_client.py:1740 HTTP Request: POST https://api.openai.com/v1/chat/completions "HTTP/1.1 200 OK"
INFO     ai_service.api.services.openai.service:service.py:361 OpenAI API status code: 200
INFO     ai_service.api.services.openai.service:service.py:390 OpenAI API response content preview: Given the focus on personality traits for birth ti...
INFO     ai_service.api.services.openai.service:service.py:460 OpenAI API call successful for questionnaire
INFO     ai_service.api.services.openai.service:service.py:304 Sending request to OpenAI API (model: gpt-4-turbo-preview, task: astrological_analysis)
INFO     httpx:_client.py:1740 HTTP Request: POST https://api.openai.com/v1/chat/completions "HTTP/1.1 200 OK"
INFO     ai_service.api.services.openai.service:service.py:361 OpenAI API status code: 200
INFO     ai_service.api.services.openai.service:service.py:390 OpenAI API response content preview: ```json
{
  "relevance_to_birth_time": 0.7,
  "ind...
INFO     ai_service.api.services.openai.service:service.py:460 OpenAI API call successful for astrological_analysis
INFO     ai_service.api.services.openai.service:service.py:304 Sending request to OpenAI API (model: gpt-4-turbo-preview, task: astrological_question_generation)
INFO     httpx:_client.py:1740 HTTP Request: POST https://api.openai.com/v1/chat/completions "HTTP/1.1 200 OK"
INFO     ai_service.api.services.openai.service:service.py:361 OpenAI API status code: 200
INFO     ai_service.api.services.openai.service:service.py:390 OpenAI API response content preview: {
  "id": "3c9d7b5e",
  "text": "Can you describe ...
INFO     ai_service.api.services.openai.service:service.py:460 OpenAI API call successful for astrological_question_generation
INFO     ai_service.api.services.session_service:session_service.py:139 Session persisted to file: 87d3ae21-7702-4ad9-93e6-2eb8bf6a129a
INFO     ai_service.api.services.session_service:session_service.py:292 Session updated: 87d3ae21-7702-4ad9-93e6-2eb8bf6a129a
INFO     tests.integration.test_sequence_flow_real:test_sequence_flow_real.py:264 Successfully saved data to /app/tests/test_data_source/test_db.json
INFO     tests.integration.test_sequence_flow_real:test_sequence_flow_real.py:291 Updated question_answers/87d3ae21-7702-4ad9-93e6-2eb8bf6a129a_2 in test database
INFO     tests.integration.test_sequence_flow_real:test_sequence_flow_real.py:957 Question progression: personality_traits -> life_events
INFO     tests.integration.test_sequence_flow_real:test_sequence_flow_real.py:876 Processing question 3: Can you describe a significant life event that felt like a turning point for you, including how old you were when it happened? (Category: life_events)
INFO     ai_service.api.services.openai.service:service.py:58 API key configured (length: 164)
INFO     ai_service.api.services.openai.service:service.py:69 Initializing direct API client
INFO     ai_service.api.services.openai.service:service.py:107 Registered client with test tracker
INFO     ai_service.api.services.openai.service:service.py:110 Initialized direct API client for OpenAI with Timeout(connect=10.0, read=90.0, write=10.0, pool=10.0)
INFO     ai_service.api.services.openai.service:service.py:148 OpenAI service initialized with model: gpt-4-turbo-preview
INFO     ai_service.api.services.openai.service:service.py:304 Sending request to OpenAI API (model: gpt-4-turbo-preview, task: questionnaire)
INFO     httpx:_client.py:1740 HTTP Request: POST https://api.openai.com/v1/chat/completions "HTTP/1.1 200 OK"
INFO     ai_service.api.services.openai.service:service.py:361 OpenAI API status code: 200
INFO     ai_service.api.services.openai.service:service.py:390 OpenAI API response content preview:
One significant turning point in my life occurred...
INFO     ai_service.api.services.openai.service:service.py:460 OpenAI API call successful for questionnaire
INFO     ai_service.api.services.openai.service:service.py:304 Sending request to OpenAI API (model: gpt-4-turbo-preview, task: astrological_analysis)
INFO     httpx:_client.py:1740 HTTP Request: POST https://api.openai.com/v1/chat/completions "HTTP/1.1 200 OK"
INFO     ai_service.api.services.openai.service:service.py:361 OpenAI API status code: 200
INFO     ai_service.api.services.openai.service:service.py:390 OpenAI API response content preview: {
  "relevance_to_birth_time": 0.7,
  "indicator_t...
INFO     ai_service.api.services.openai.service:service.py:460 OpenAI API call successful for astrological_analysis
INFO     ai_service.api.services.openai.service:service.py:304 Sending request to OpenAI API (model: gpt-4-turbo-preview, task: astrological_question_generation)
INFO     httpx:_client.py:1740 HTTP Request: POST https://api.openai.com/v1/chat/completions "HTTP/1.1 200 OK"
INFO     ai_service.api.services.openai.service:service.py:361 OpenAI API status code: 200
INFO     ai_service.api.services.openai.service:service.py:390 OpenAI API response content preview: ```json
{
  "id": "q4_timing_pref_1985",
  "text":...
INFO     ai_service.api.services.openai.service:service.py:460 OpenAI API call successful for astrological_question_generation
INFO     ai_service.api.services.session_service:session_service.py:139 Session persisted to file: 87d3ae21-7702-4ad9-93e6-2eb8bf6a129a
INFO     ai_service.api.services.session_service:session_service.py:292 Session updated: 87d3ae21-7702-4ad9-93e6-2eb8bf6a129a
INFO     tests.integration.test_sequence_flow_real:test_sequence_flow_real.py:264 Successfully saved data to /app/tests/test_data_source/test_db.json
INFO     tests.integration.test_sequence_flow_real:test_sequence_flow_real.py:291 Updated question_answers/87d3ae21-7702-4ad9-93e6-2eb8bf6a129a_3c9d7b5e in test database
INFO     tests.integration.test_sequence_flow_real:test_sequence_flow_real.py:957 Question progression: life_events -> timing_preferences
INFO     tests.integration.test_sequence_flow_real:test_sequence_flow_real.py:876 Processing question 4: Considering your daily routine, which time of the day do you feel most energetic and productive? Please select the option that best describes your natural preference, not influenced by your current job or responsibilities. (Category: timing_preferences)
INFO     ai_service.api.services.openai.service:service.py:58 API key configured (length: 164)
INFO     ai_service.api.services.openai.service:service.py:69 Initializing direct API client
INFO     ai_service.api.services.openai.service:service.py:107 Registered client with test tracker
INFO     ai_service.api.services.openai.service:service.py:110 Initialized direct API client for OpenAI with Timeout(connect=10.0, read=90.0, write=10.0, pool=10.0)
INFO     ai_service.api.services.openai.service:service.py:148 OpenAI service initialized with model: gpt-4-turbo-preview
INFO     ai_service.api.services.openai.service:service.py:304 Sending request to OpenAI API (model: gpt-4-turbo-preview, task: questionnaire)
INFO     httpx:_client.py:1740 HTTP Request: POST https://api.openai.com/v1/chat/completions "HTTP/1.1 200 OK"
INFO     ai_service.api.services.openai.service:service.py:361 OpenAI API status code: 200
INFO     ai_service.api.services.openai.service:service.py:390 OpenAI API response content preview: In terms of my daily routine and natural energy cy...
INFO     ai_service.api.services.openai.service:service.py:460 OpenAI API call successful for questionnaire
INFO     ai_service.api.services.openai.service:service.py:304 Sending request to OpenAI API (model: gpt-4-turbo-preview, task: astrological_analysis)
INFO     httpx:_client.py:1740 HTTP Request: POST https://api.openai.com/v1/chat/completions "HTTP/1.1 200 OK"
INFO     ai_service.api.services.openai.service:service.py:361 OpenAI API status code: 200
INFO     ai_service.api.services.openai.service:service.py:390 OpenAI API response content preview: ```json
{
  "relevance_to_birth_time": 0.6,
  "ind...
INFO     ai_service.api.services.openai.service:service.py:460 OpenAI API call successful for astrological_analysis
INFO     ai_service.api.services.openai.service:service.py:304 Sending request to OpenAI API (model: gpt-4-turbo-preview, task: astrological_question_generation)
INFO     httpx:_client.py:1740 HTTP Request: POST https://api.openai.com/v1/chat/completions "HTTP/1.1 200 OK"
INFO     ai_service.api.services.openai.service:service.py:361 OpenAI API status code: 200
INFO     ai_service.api.services.openai.service:service.py:390 OpenAI API response content preview: ```json
{
  "id": "5f2b10e8-8dfe-4d01-9fd3-2e8ec72...
INFO     ai_service.api.services.openai.service:service.py:460 OpenAI API call successful for astrological_question_generation
INFO     ai_service.api.services.session_service:session_service.py:139 Session persisted to file: 87d3ae21-7702-4ad9-93e6-2eb8bf6a129a
INFO     ai_service.api.services.session_service:session_service.py:292 Session updated: 87d3ae21-7702-4ad9-93e6-2eb8bf6a129a
INFO     tests.integration.test_sequence_flow_real:test_sequence_flow_real.py:264 Successfully saved data to /app/tests/test_data_source/test_db.json
INFO     tests.integration.test_sequence_flow_real:test_sequence_flow_real.py:291 Updated question_answers/87d3ae21-7702-4ad9-93e6-2eb8bf6a129a_q4_timing_pref_1985 in test database
INFO     tests.integration.test_sequence_flow_real:test_sequence_flow_real.py:957 Question progression: timing_preferences -> relationships
INFO     tests.integration.test_sequence_flow_real:test_sequence_flow_real.py:876 Processing question 5: Reflecting on your closest relationships, how do you typically find yourself in the role of: the initiator who reaches out and makes plans, the responder who waits for others to take the lead, a mix of both depending on the situation, or you generally prefer solitude and engaging in deep, meaningful connections with very few people? (Category: relationships)
INFO     ai_service.api.services.openai.service:service.py:58 API key configured (length: 164)
INFO     ai_service.api.services.openai.service:service.py:69 Initializing direct API client
INFO     ai_service.api.services.openai.service:service.py:107 Registered client with test tracker
INFO     ai_service.api.services.openai.service:service.py:110 Initialized direct API client for OpenAI with Timeout(connect=10.0, read=90.0, write=10.0, pool=10.0)
INFO     ai_service.api.services.openai.service:service.py:148 OpenAI service initialized with model: gpt-4-turbo-preview
INFO     ai_service.api.services.openai.service:service.py:304 Sending request to OpenAI API (model: gpt-4-turbo-preview, task: questionnaire)
INFO     httpx:_client.py:1740 HTTP Request: POST https://api.openai.com/v1/chat/completions "HTTP/1.1 200 OK"
INFO     ai_service.api.services.openai.service:service.py:361 OpenAI API status code: 200
INFO     ai_service.api.services.openai.service:service.py:390 OpenAI API response content preview: In my closest relationships, I find myself predomi...
INFO     ai_service.api.services.openai.service:service.py:460 OpenAI API call successful for questionnaire
INFO     ai_service.api.services.openai.service:service.py:304 Sending request to OpenAI API (model: gpt-4-turbo-preview, task: astrological_question_generation)
INFO     httpx:_client.py:1740 HTTP Request: POST https://api.openai.com/v1/chat/completions "HTTP/1.1 200 OK"
INFO     ai_service.api.services.openai.service:service.py:361 OpenAI API status code: 200
INFO     ai_service.api.services.openai.service:service.py:390 OpenAI API response content preview: ```json
{
  "id": "74f8c4a5",
  "text": "Reflectin...
INFO     ai_service.api.services.openai.service:service.py:460 OpenAI API call successful for astrological_question_generation
INFO     ai_service.api.services.session_service:session_service.py:139 Session persisted to file: 87d3ae21-7702-4ad9-93e6-2eb8bf6a129a
INFO     ai_service.api.services.session_service:session_service.py:292 Session updated: 87d3ae21-7702-4ad9-93e6-2eb8bf6a129a
INFO     tests.integration.test_sequence_flow_real:test_sequence_flow_real.py:264 Successfully saved data to /app/tests/test_data_source/test_db.json
INFO     tests.integration.test_sequence_flow_real:test_sequence_flow_real.py:291 Updated question_answers/87d3ae21-7702-4ad9-93e6-2eb8bf6a129a_5f2b10e8-8dfe-4d01-9fd3-2e8ec72e9b2c in test database
INFO     tests.integration.test_sequence_flow_real:test_sequence_flow_real.py:957 Question progression: relationships -> career
INFO     tests.integration.test_sequence_flow_real:test_sequence_flow_real.py:984 Questionnaire unique question ratio: 0.83 (5 unique of 6 total)
INFO     tests.integration.test_sequence_flow_real:test_sequence_flow_real.py:989 Completed questionnaire with 6 questions answered
INFO     ai_service.api.services.openai.service:service.py:304 Sending request to OpenAI API (model: gpt-4-turbo-preview, task: birth_time_rectification)
INFO     httpx:_client.py:1740 HTTP Request: POST https://api.openai.com/v1/chat/completions "HTTP/1.1 200 OK"
INFO     ai_service.api.services.openai.service:service.py:361 OpenAI API status code: 200
INFO     ai_service.api.services.openai.service:service.py:390 OpenAI API response content preview: ```json
{
  "confidence": 0.75,
  "indicators": [
...
INFO     ai_service.api.services.openai.service:service.py:460 OpenAI API call successful for birth_time_rectification
INFO     ai_service.api.services.session_service:session_service.py:139 Session persisted to file: 87d3ae21-7702-4ad9-93e6-2eb8bf6a129a
INFO     ai_service.api.services.session_service:session_service.py:292 Session updated: 87d3ae21-7702-4ad9-93e6-2eb8bf6a129a
INFO     tests.integration.test_sequence_flow_real:test_sequence_flow_real.py:264 Successfully saved data to /app/tests/test_data_source/test_db.json
INFO     tests.integration.test_sequence_flow_real:test_sequence_flow_real.py:291 Updated questionnaire_completion/87d3ae21-7702-4ad9-93e6-2eb8bf6a129a in test database
INFO     tests.integration.test_sequence_flow_real:test_sequence_flow_real.py:997 Questionnaire completion status: True
INFO     tests.integration.test_sequence_flow_real:test_sequence_flow_real.py:998 Rectification confidence based on questionnaire: 67.5
INFO     tests.integration.test_sequence_flow_real:test_sequence_flow_real.py:461 Starting test phase: birth_time_rectification
INFO     tests.integration.test_sequence_flow_real:test_sequence_flow_real.py:1007 Step 7: Performing birth time rectification with real astrological calculations
INFO     ai_service.database.repositories:repositories.py:63 Using file-based storage at /app/ai_service/data/charts for tests
INFO     ai_service.core.rectification.main:main.py:252 Registered file-based chart_repository service
INFO     ai_service.core.rectification.event_analysis:event_analysis.py:117 Extracted life event: children - Given the question category of physical traits for birth time rectification, I would describe myself as having a medium build with a height that is slightly above average. My most distinctive physical feature has been my thick, wavy hair, which has a noticeable auburn tint that has remained unchanged throughout my life. Additionally, I have almond-shaped eyes that many say are expressive and a clear, olive-toned skin complexion that tans easily but seldom burns. These traits have been a consistent part of my appearance from childhood into adulthood, providing a stable reference for any astrological analysis aimed at determining my exact birth time. (unknown)
INFO     ai_service.core.rectification.event_analysis:event_analysis.py:117 Extracted life event: children - Given the focus on personality traits for birth time rectification, I would describe myself as deeply introspective and analytical, with a strong inclination towards seeking knowledge and understanding complex topics. I've always had a temperament that is more reserved and cautious, preferring to observe and process my environment and interactions thoroughly before engaging. This introspection often leads me to be perceived as aloof or distant in initial meetings, but I form deep, meaningful connections with those I choose to open up to. My emotional responses are typically measured and controlled; I rarely react impulsively, favoring a more thoughtful and composed approach to dealing with emotional situations. This consistency in seeking depth, both in knowledge and relationships, coupled with a methodical approach to emotional responses, has been a hallmark of my personality throughout my life. (unknown)
INFO     ai_service.core.rectification.event_analysis:event_analysis.py:117 Extracted life event: career_change - One significant turning point in my life occurred when I was 25 years old, around late 2010. I had been working in a relatively stable but unfulfilling job in Pune for a couple of years after completing my education. The turning point came when I decided to resign from my job to pursue higher education abroad. This decision was fueled by a deep desire for personal growth and a yearning to expand my horizons beyond what I had known all my life in Maharashtra. The emotional impact of this decision was profound; it was a mix of fear, excitement, and a sense of stepping into the unknown. This period marked a significant shift in my life's trajectory, setting me on a path that was vastly different from anything I had envisioned for myself up to that point. The process of making this decision, from contemplation to taking action, spanned several months in 2010, but the resignation and the move itself became the most defining moments of that year and, indeed, my adult life. (2010-06-15)
INFO     ai_service.core.rectification.event_analysis:event_analysis.py:117 Extracted life event: career_change - In terms of my daily routine and natural energy cycles, I've always been a morning person. I find myself most energetic and productive in the early hours of the day, typically from 5:00 AM to 9:00 AM. This is the time when my mind is the clearest and I can focus on my tasks with minimal distraction. My energy levels tend to dip after lunch, around 2:00 PM, and I rarely find myself being productive in the late evenings. This pattern has been consistent regardless of my job or other responsibilities. (unknown)
INFO     ai_service.core.rectification.event_analysis:event_analysis.py:117 Extracted life event: children - In my closest relationships, I find myself predominantly in the role of the initiator, always reaching out and making plans to bring people together. This tendency has been particularly noticeable since my early twenties, around the age of 22 or 23, which coincides with a period of significant personal growth and the development of a more outgoing aspect of my personality. This role as an initiator has played out in both my personal and professional life, leading to deep, meaningful connections with a select group of individuals. My approach to initiating plans or gatherings often involves thoughtful consideration of the interests and preferences of those I am inviting, which has helped in strengthening these relationships over the years. (unknown)
INFO     ai_service.core.rectification.event_analysis:event_analysis.py:123 Extracted 5 life events from 5 answers
INFO     ai_service.core.rectification.main:main.py:291 Using OpenAI for advanced rectification analysis
INFO     ai_service.api.services.openai.service:service.py:304 Sending request to OpenAI API (model: gpt-4-turbo-preview, task: birth_time_rectification)
INFO     ai_service.database.repositories:repositories.py:124 Database connection pool created
INFO     ai_service.database.repositories:repositories.py:177 Database tables initialized
INFO     httpx:_client.py:1740 HTTP Request: POST https://api.openai.com/v1/chat/completions "HTTP/1.1 200 OK"
INFO     ai_service.api.services.openai.service:service.py:361 OpenAI API status code: 200
INFO     ai_service.api.services.openai.service:service.py:390 OpenAI API response content preview: Rectifying a birth time using both Vedic and Weste...
INFO     ai_service.api.services.openai.service:service.py:460 OpenAI API call successful for birth_time_rectification
INFO     ai_service.core.rectification.main:main.py:378 Using text-based extraction as fallback for JSON parsing
INFO     ai_service.core.rectification.main:main.py:447 AI rectification successful: 1985-10-24 14:30:00, confidence: 50.0
INFO     ai_service.core.rectification.main:main.py:69 Rectifying birth time for 1985-10-24 14:30:00 at 18.5204, 73.8567
INFO     ai_service.api.services.openai.service:service.py:304 Sending request to OpenAI API (model: gpt-4-turbo-preview, task: birth_time_rectification)
INFO     httpx:_client.py:1740 HTTP Request: POST https://api.openai.com/v1/chat/completions "HTTP/1.1 200 OK"
INFO     ai_service.api.services.openai.service:service.py:361 OpenAI API status code: 200
INFO     ai_service.api.services.openai.service:service.py:390 OpenAI API response content preview: ```json
{
  "rectified_time": "14:10",
  "adjustme...
INFO     ai_service.api.services.openai.service:service.py:460 OpenAI API call successful for birth_time_rectification
INFO     ai_service.core.rectification.methods.ai_rectification:ai_rectification.py:272 Extracted JSON using regex
INFO     ai_service.core.rectification.methods.ai_rectification:ai_rectification.py:372 AI rectification result: 14:10 with 85.0% confidence
INFO     ai_service.core.rectification.main:main.py:481 Questionnaire-based rectification successful: 1985-10-24 14:10:00, confidence: 85.0
INFO     ai_service.core.rectification.methods.transit_analysis:transit_analysis.py:280 Transit analysis result: 1985-10-24 12:30:00, score: 17.00, confidence: 84.0
INFO     ai_service.core.rectification.methods.transit_analysis:transit_analysis.py:281 Based on 1 events with 3 significant aspects
INFO     ai_service.core.rectification.main:main.py:498 Transit analysis successful: 1985-10-24 12:30:00, confidence: 84.0
INFO     ai_service.core.rectification.methods.solar_arc:solar_arc.py:30 Using solar arc directions for rectification
INFO     ai_service.core.rectification.methods.solar_arc:solar_arc.py:136 Solar arc rectification result: 1985-10-24 16:15:00, confidence: 68.66666666666667
INFO     ai_service.core.rectification.main:main.py:514 Solar arc rectification: 1985-10-24 16:15:00, confidence: 68.66666666666667
INFO     ai_service.core.rectification.main:main.py:691 Storing rectified chart with ID: rectification_None_fe3341cb
INFO     ai_service.database.repositories:repositories.py:279 Stored chart chart_ba77574f09 in database
INFO     ai_service.core.rectification.utils.storage:storage.py:62 Stored rectified chart with ID: rectified_chart_rectification_None_fe3341cb_a187a6ad using repository
INFO     ai_service.database.repositories:repositories.py:63 Using file-based storage at /app/ai_service/data/charts for tests
INFO     ai_service.core.rectification.utils.storage:storage.py:80 Stored rectified chart with ID: rectified_chart_rectification_None_fe3341cb_a187a6ad at path: /app/ai_service/data/charts/rectified_chart_rectification_None_fe3341cb_a187a6ad.json
INFO     ai_service.core.rectification.utils.storage:storage.py:89 Stored rectified chart with ID: rectified_chart_rectification_None_fe3341cb_a187a6ad at additional path: /app/ai_service/data/charts/rectified_chart_rectification_None_fe3341cb_a187a6ad.json
INFO     ai_service.core.rectification.utils.storage:storage.py:99 Stored rectified chart with ID: rectified_chart_rectification_None_fe3341cb_a187a6ad at test path: /app/ai_service/tests/test_data_source/charts/rectified_chart_rectification_None_fe3341cb_a187a6ad.json
INFO     ai_service.core.rectification.utils.storage:storage.py:102 Chart rectified_chart_rectification_None_fe3341cb_a187a6ad stored at the following locations: /app/ai_service/data/charts, /app/ai_service/data/charts, /app/ai_service/tests/test_data_source/charts
INFO     tests.integration.test_sequence_flow_real:test_sequence_flow_real.py:264 Successfully saved data to /app/tests/test_data_source/test_db.json
INFO     tests.integration.test_sequence_flow_real:test_sequence_flow_real.py:291 Updated rectifications/rectification_None_fe3341cb in test database
INFO     tests.integration.test_sequence_flow_real:test_sequence_flow_real.py:1072 Rectification completed with ID: rectification_None_fe3341cb
INFO     tests.integration.test_sequence_flow_real:test_sequence_flow_real.py:1073 Original time: None, Rectified time: 1985-10-24 14:17:00
INFO     tests.integration.test_sequence_flow_real:test_sequence_flow_real.py:461 Starting test phase: chart_comparison
INFO     tests.integration.test_sequence_flow_real:test_sequence_flow_real.py:1077 Step 8: Comparing original and rectified charts
INFO     ai_service.database.repositories:repositories.py:489 Retrieved chart rectified_chart_rectification_None_fe3341cb_a187a6ad from file /app/ai_service/data/charts/rectified_chart_rectification_None_fe3341cb_a187a6ad.json
INFO     ai_service.database.repositories:repositories.py:345 Retrieved chart rectified_chart_rectification_None_fe3341cb_a187a6ad from file storage
INFO     ai_service.database.repositories:repositories.py:827 Charts exist in file storage but not in database. Using file storage for comparison comp_1a560171-0a21-412c-909a-273ea0f781ef
INFO     ai_service.database.repositories:repositories.py:958 Comparison comp_1a560171-0a21-412c-909a-273ea0f781ef stored in file /app/ai_service/data/charts/comparison_comp_1a560171-0a21-412c-909a-273ea0f781ef.json
INFO     ai_service.services.chart_service:chart_service.py:969 Chart comparison completed and stored with ID: comp_1a560171-0a21-412c-909a-273ea0f781ef
INFO     tests.integration.test_sequence_flow_real:test_sequence_flow_real.py:264 Successfully saved data to /app/tests/test_data_source/test_db.json
INFO     tests.integration.test_sequence_flow_real:test_sequence_flow_real.py:291 Updated comparisons/comp_1a560171-0a21-412c-909a-273ea0f781ef in test database
INFO     tests.integration.test_sequence_flow_real:test_sequence_flow_real.py:1097 Chart comparison completed with ID: comp_1a560171-0a21-412c-909a-273ea0f781ef
INFO     tests.integration.test_sequence_flow_real:test_sequence_flow_real.py:461 Starting test phase: chart_export
INFO     tests.integration.test_sequence_flow_real:test_sequence_flow_real.py:1101 Step 9: Exporting rectified chart
INFO     ai_service.services.chart_service:chart_service.py:1492 Exporting chart rectified_chart_rectification_None_fe3341cb_a187a6ad in pdf format
INFO     ai_service.database.repositories:repositories.py:489 Retrieved chart rectified_chart_rectification_None_fe3341cb_a187a6ad from file /app/ai_service/data/charts/rectified_chart_rectification_None_fe3341cb_a187a6ad.json
INFO     ai_service.database.repositories:repositories.py:345 Retrieved chart rectified_chart_rectification_None_fe3341cb_a187a6ad from file storage
INFO     ai_service.services.chart_service:chart_service.py:701 Retrieved chart with ID: rectified_chart_rectification_None_fe3341cb_a187a6ad
INFO     ai_service.services.chart_service:chart_service.py:2218 Generated chart PDF: /app/ai_service/data/exports/export_rectified_chart_rectification_None_fe3341cb_a187a6ad_60631c65.pdf
INFO     ai_service.database.repositories:repositories.py:1098 Chart exists in file storage but not in database. Using file storage for export export_rectified_chart_rectification_None_fe3341cb_a187a6ad_60631c65
INFO     ai_service.database.repositories:repositories.py:1215 Export export_rectified_chart_rectification_None_fe3341cb_a187a6ad_60631c65 stored in file /app/ai_service/data/charts/export_export_rectified_chart_rectification_None_fe3341cb_a187a6ad_60631c65.json
INFO     tests.integration.test_sequence_flow_real:test_sequence_flow_real.py:264 Successfully saved data to /app/tests/test_data_source/test_db.json
INFO     tests.integration.test_sequence_flow_real:test_sequence_flow_real.py:291 Updated exports/export_rectified_chart_rectification_None_fe3341cb_a187a6ad_60631c65 in test database
INFO     tests.integration.test_sequence_flow_real:test_sequence_flow_real.py:1123 Chart export completed with ID: export_rectified_chart_rectification_None_fe3341cb_a187a6ad_60631c65
INFO     tests.integration.test_sequence_flow_real:test_sequence_flow_real.py:1124 Export download URL: /api/chart/export/export_rectified_chart_rectification_None_fe3341cb_a187a6ad_60631c65/download
INFO     tests.integration.test_sequence_flow_real:test_sequence_flow_real.py:264 Successfully saved data to /app/tests/test_data_source/output_birt_data.json
INFO     ai_service.services.chart_service:chart_service.py:701 Retrieved chart with ID: chart_4e4890db59
INFO     ai_service.database.repositories:repositories.py:489 Retrieved chart rectified_chart_rectification_None_fe3341cb_a187a6ad from file /app/ai_service/data/charts/rectified_chart_rectification_None_fe3341cb_a187a6ad.json
INFO     ai_service.database.repositories:repositories.py:345 Retrieved chart rectified_chart_rectification_None_fe3341cb_a187a6ad from file storage
INFO     ai_service.services.chart_service:chart_service.py:701 Retrieved chart with ID: rectified_chart_rectification_None_fe3341cb_a187a6ad
INFO     tests.integration.test_sequence_flow_real:test_sequence_flow_real.py:264 Successfully saved data to /app/tests/test_data_source/test_charts_data.json
INFO     tests.integration.test_sequence_flow_real:test_sequence_flow_real.py:1189 Complete test sequence flow executed successfully with REAL implementations
INFO     tests.integration.test_sequence_flow_real:test_sequence_flow_real.py:1190 Output data saved to /app/tests/test_data_source/output_birt_data.json
INFO     tests.integration.test_sequence_flow_real:test_sequence_flow_real.py:1191 Chart visualization data saved to /app/tests/test_data_source/test_charts_data.json
INFO     tests.integration.test_sequence_flow_real:test_sequence_flow_real.py:1195 Cleaning up resources...
INFO     ai_service.database.repositories:repositories.py:1434 Cancelling 1 pending database initialization tasks
INFO     ai_service.database.repositories:repositories.py:1465 Handled exception during repository cleanup: `pydantic.config.Extra` is deprecated, use literal values instead (e.g. `extra='allow'`). Deprecated in Pydantic V2.0 to be removed in V3.0. See Pydantic V2 Migration Guide at https://errors.pydantic.dev/2.3/migration/
INFO     ai_service.database.repositories:repositories.py:1420 Closing database connection pool
INFO     tests.integration.test_sequence_flow_real:test_sequence_flow_real.py:1229 Cleaned up chart repository resources
PASSED                                                                   [100%]

======================== 1 passed in 156.08s (0:02:36) =========================
.venvvicd@Vics-MacBook-Air containerised-birth-time-rectifier % 
