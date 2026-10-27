"""FAQ and error-code content (stored in SQL by `manage.py seed`)."""

# category, question, answer, keywords
FAQS = [
    ("General", "What is ElectroLab?",
     "ElectroLab is a free library of embedded-systems and IoT projects for ESP32, Arduino and Raspberry Pi Pico. "
     "Every project has a parts list, wiring diagram, copy-ready code, step-by-step instructions and a video tutorial.",
     "about site what is electrolab"),
    ("General", "Is ElectroLab free to use?",
     "Yes. Browsing, copying and downloading code, and the AI assistant are all free. You never need an account.",
     "price cost free pay account sign up"),
    ("Projects", "How do I copy or download the code?",
     "Open a project and choose the Code tab. Press Copy to put the sketch on your clipboard, Download to save the file, "
     "or use 'Download project (.zip)' at the top of the page to get the README and every code file together.",
     "copy download code sketch zip file"),
    ("Projects", "Which boards do the projects use?",
     "The starter projects use the ESP32, ESP32-CAM, Arduino Uno and Raspberry Pi Pico. Each project page shows the exact board "
     "and the filter on the Projects page lets you search by board.",
     "boards esp32 arduino pico hardware microcontroller"),
    ("Projects", "I am a complete beginner. Where should I start?",
     "Start with a Beginner project such as the Ultrasonic Distance Meter or the Pico Traffic Light. They take 20-30 minutes, "
     "use few parts and teach wiring, uploading code and reading the Serial Monitor.",
     "beginner start first easy learn new"),
    ("Projects", "How do wiring diagrams work?",
     "Open the Wiring tab. The diagram is drawn automatically from the connection table: each coloured wire joins a board pin on the "
     "left to a component pin on the right. Hover a wire to see the exact connection.",
     "wiring diagram connections pins circuit schematic"),
    ("AI assistant", "What can the AI assistant do?",
     "It answers questions from the FAQ and project guides, explains error codes such as 404 or 429, and can explain code line by line. "
     "If it cannot answer, it opens a support ticket so a person can follow up.",
     "ai assistant chatbot help bot ask"),
    ("AI assistant", "Does the assistant store my chats?",
     "Chat messages and your thumbs-up/down feedback are stored so we can improve answers. Do not type passwords or personal secrets "
     "into the chat. Support tickets are stored only to answer your request.",
     "privacy data store log chat feedback"),
    ("AI assistant", "What happens if the assistant cannot answer?",
     "It creates a support ticket (for example ELT-0007) and tells you the reference. You can add your email in the chat "
     "or on the Support page so we can reply, and check the ticket status with the reference.",
     "ticket support cannot answer human contact"),
    ("Support", "How do I contact support or check a ticket?",
     "Use the Support page: send a new request, or enter your ticket reference (ELT-0007) to see its status.",
     "contact support ticket status email help"),
    ("Troubleshooting", "My ESP32 will not upload code. What should I try?",
     "Use a data-capable USB cable, select the correct board and COM port, and hold the BOOT button while 'Connecting...' appears. "
     "For the ESP32-CAM connect GPIO0 to GND while flashing, then reset.",
     "upload fail connecting esp32 flash serial port boot"),
    ("Troubleshooting", "Why do I see a 'Page not found' error?",
     "The address does not exist or a project was renamed. Check the spelling or go to the Projects page. This is HTTP error 404 "
     "(site code EL-1001 when a project guide is missing).",
     "404 not found missing page broken link"),
    ("Troubleshooting", "Is it safe to switch mains-voltage devices?",
     "Treat mains voltage as dangerous. Test relay projects with low-voltage loads first, use a rated enclosed relay board, fuse the circuit "
     "and never touch live wiring. If unsure, ask a qualified electrician.",
     "mains safety relay ac danger voltage"),
]

# code, title, meaning, fix, http_status
ERROR_CODES = [
    ("400", "Bad Request", "The server could not understand the request, usually because of malformed data or an empty message.",
     "Check what you typed or submitted, refresh the page and try again.", 400),
    ("401", "Unauthorized", "The page needs you to sign in first and no valid login was supplied.",
     "Sign in (for the admin area use your staff account) and retry.", 401),
    ("403", "Forbidden", "You are recognised but not allowed to open this resource. "
     "A missing or expired security (CSRF) token can also cause it.", "Reload the page to get a fresh token, or ask an admin for access.", 403),
    ("404", "Not Found", "The address does not exist on this site: the link is wrong or the page was moved.",
     "Check the spelling, go back to the Projects page, or search for the project.", 404),
    ("429", "Too Many Requests", "You sent too many AI requests in a short time, so the limiter paused you.",
     "Wait about a minute, then try again. Avoid repeatedly pressing Send.", 429),
    ("500", "Internal Server Error", "Something went wrong inside the server while building this page. It is not your fault.",
     "Reload after a moment. If it keeps happening, open a support ticket with the page address.", 500),
    ("503", "Service Unavailable", "The server or a dependency (database or AI provider) is temporarily down or waking up.",
     "Wait 30-60 seconds (free hosting sleeps when idle) and retry. See the Health page for status.", 503),
    ("EL-1001", "Project guide not found", "Site-specific code: the project slug in the address is not in the catalogue.",
     "Open the Projects page and pick a guide from the list.", 404),
    ("EL-2001", "AI provider unavailable", "Site-specific code: every external AI model timed out, so the built-in engine answered instead.",
     "Your answer is still valid but shorter. Retry later for a fuller explanation.", None),
]
