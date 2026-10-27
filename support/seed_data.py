"""Initial content loaded by migration 0002. Edit it later from /admin/ (no redeploy needed)."""

FAQS = [
    # (category, question, answer, keywords)
    ('Getting started', 'What is KILO?',
     'KILO is a minimalist calorie and workout tracker. You log meals and workouts, set daily targets, and the '
     'Today page shows how you are doing against them.',
     'kilo app about purpose fitness tracker what'),
    ('Getting started', 'Is KILO free to use?',
     'Yes. KILO is a free project with no payments or subscriptions. Create an account on the Sign up page and '
     'start logging straight away.',
     'free cost price pay subscription premium account signup register'),
    ('Getting started', 'Can I use KILO on my phone?',
     'Yes. Every page is responsive, so KILO works in a phone browser as well as on a computer, and the chat '
     'assistant resizes to fit small screens.',
     'mobile phone responsive tablet device screen android iphone'),
    ('Tracking', 'How do I log a meal?',
     'Open the Meals page, fill in the meal name, calories and optional protein, carbs and fat, then press '
     'Add meal. You can also use Look up food to fill in the numbers automatically.',
     'log add meal food eat breakfast lunch dinner snack enter record'),
    ('Tracking', 'How do I log a workout?',
     'Open the Workouts page, enter the exercise name, category, duration and calories burned. For lifting you '
     'can also add sets, reps and weight, and KILO works out the total volume.',
     'log add workout exercise gym training lift run cardio record'),
    ('Tracking', 'How do I delete a meal or workout I logged by mistake?',
     'Press the x button at the end of the entry on the Meals or Workouts page. Deleting cannot be undone.',
     'delete remove undo mistake wrong entry edit'),
    ('Tracking', 'Can I look up the calories of a food?',
     'Yes. On the Meals page type a food name under Look up food and pick a result. KILO searches the Open Food '
     'Facts database and fills in calories and macros per portion. If that service is slow or offline, a built-in '
     'list of common foods is used instead.',
     'lookup search calories food nutrition database macros open food facts barcode'),
    ('Goals and progress', 'How are my remaining calories calculated?',
     'Remaining = daily goal - calories eaten + calories burned. If you eat more than that allows, the Today '
     'page shows how many calories you are over.',
     'remaining calculate calculation net burned eaten left budget formula'),
    ('Goals and progress', 'How do I change my calorie or protein goal?',
     'Open the Goals page, change your daily calories, daily protein or weekly workouts, and press Save goals. '
     'The Today page updates straight away.',
     'change set update goal target calories protein weekly workouts'),
    ('Goals and progress', 'What does the red ring on the Today page mean?',
     'The ring shows calories eaten today as a share of your daily goal. It stops at a full circle even if you '
     'go over, and the Remaining figure turns red when you are over your goal.',
     'ring circle chart progress today dashboard red bar week'),
    ('Account and data', 'Is my data private?',
     'Each account only ever sees its own meals, workouts and goals. Passwords are stored hashed. Chat messages '
     'and feedback are stored so answers can be improved, with your IP address kept only as a one-way hash, so '
     'please do not type sensitive details into the chat.',
     'privacy private data safe secure security password store delete gdpr'),
    ('Account and data', 'I forgot my password. What can I do?',
     'Password reset by email is not available yet. Open a support ticket from the Support page or ask the '
     'assistant, and include your username so it can be looked into.',
     'forgot reset password login locked sign in cannot access account'),
    ('Account and data', 'Does KILO have an API?',
     'Yes. KILO has a JSON REST API under /api/ for meals, workouts, goals and a daily summary. Create a token '
     'with POST /api/auth/token/ and send it as an Authorization: Token header. BACKEND.md describes every endpoint.',
     'api rest json token developer integrate endpoint programmatic'),
    ('Assistant', 'What can the KILO assistant do?',
     'It answers questions using this FAQ, explains error codes such as 404 or 429, and opens a support ticket '
     'when it cannot answer so that a person can follow up.',
     'assistant chatbot bot ai help capabilities features chat'),
    ('Assistant', 'What happens if the assistant cannot answer my question?',
     'It creates a support ticket with your question and gives you a ticket number such as TKT-00012. You can '
     'add your email address to the ticket in the chat so you can be contacted.',
     'cannot unknown ticket support escalate human unanswered contact'),
]

ERROR_CODES = [
    # (code, http_status, title, meaning, how_to_fix, position)
    ('400', 400, 'Bad Request',
     'The server could not understand the request because something in it was malformed or missing, for '
     'example an invalid date or a negative number of calories.',
     'Check the values you entered (dates as YYYY-MM-DD, numbers above zero) and try again.',
     1),
    ('401', 401, 'Unauthorized',
     'The request needs valid credentials and none were supplied or they were not accepted. For the API this '
     'means a missing or wrong token.',
     'Sign in again. For the API, send the header "Authorization: Token <your key>" using a token from '
     'POST /api/auth/token/.',
     2),
    ('403', 403, 'Forbidden',
     'The server understood the request but refused it. In KILO this usually means a form was submitted from '
     'an expired page (a CSRF check failed).',
     'Reload the page and submit the form again. If it keeps happening, make sure cookies are enabled.',
     3),
    ('404', 404, 'Not Found',
     'The page, meal, workout or API item you asked for does not exist, or it belongs to another account. The '
     'address may also be mistyped.',
     'Check the address, go back to the Today page, or use the menu to find what you were looking for.',
     4),
    ('429', 429, 'Too Many Requests',
     'You sent too many requests in a short time, so KILO is asking you to slow down. The chat assistant allows '
     '20 messages per minute and the sign-in API 20 attempts per minute.',
     'Wait about a minute and try again.',
     5),
    ('500', 500, 'Internal Server Error',
     'Something went wrong inside KILO while handling your request. It is a problem with the app, not with '
     'your device or your data.',
     'Reload after a few moments. If it continues, tell the assistant what you were doing so it can open a '
     'support ticket.',
     6),
    ('503', 503, 'Service Unavailable',
     'KILO is temporarily unable to handle requests, usually because of maintenance or because its database is '
     'unavailable.',
     'Wait a few minutes and try again. The System status page shows which services are running.',
     7),
    ('KILO-1001', 400, 'Invalid chat message',
     'KILO-specific code. The chat assistant rejected your message because it was empty or longer than 500 '
     'characters.',
     'Type a message between 1 and 500 characters. For longer questions use the Support page.',
     8),
    ('KILO-2001', None, 'Food lookup unavailable',
     'KILO-specific code. The Open Food Facts nutrition service did not answer within 4 seconds, so KILO '
     'showed results from its built-in list of common foods instead.',
     'Nothing is broken. Pick a result from the built-in list, or type the calories in yourself and try the '
     'lookup again later.',
     9),
]
