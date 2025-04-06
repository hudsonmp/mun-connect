#!/bin/bash

echo "Checking for Next.js servers running on ports 3000-3005..."

for port in {3000..3005}
do
  # Find process running on the port
  pid=$(lsof -i :$port -t 2>/dev/null)
  
  if [ -n "$pid" ]; then
    echo "Found process $pid running on port $port. Killing..."
    kill -9 $pid
    echo "Process on port $port terminated."
  else
    echo "No process found on port $port."
  fi
done

echo "All Next.js server instances checked."
echo "To restart the testing platform, run: npm run test-platform" 