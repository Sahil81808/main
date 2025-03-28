echo -e '#!/bin/bash\nwhile true\ndo\n  curl https://google.com > /dev/null 2>&1\n  sleep 60\ndone' > keepalive.sh && chmod +x keepalive.sh
nohup bash keepalive.sh &