echo -e '#!/bin/bash\nwhile true\ndo\n  python3 main.py || echo "Bot crashed or exited, restarting..."\n  sleep 1\ndone' > runbot.sh && chmod +x runbot.sh
