#!/bin/bash
# set_api_key.sh - Show instructions for setting the Anthropic API key

# Open the workflow configuration in Alfred Preferences
osascript -e '
tell application "Alfred"
    run trigger "config" in workflow "com.neub.alfred.ai-ask"
end tell
' 2>/dev/null

echo "To set your API key:

1. Open Alfred Preferences (Cmd+,)
2. Go to Workflows > AI Quick Ask
3. Click the [x] icon in the top-right to open workflow variables
4. Set ANTHROPIC_API_KEY to your key from console.anthropic.com

Your key will be stored securely in Alfred's workflow configuration."
