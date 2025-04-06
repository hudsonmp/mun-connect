# MUN Connect Testing Platform Summary

## Major Modifications

1. **Database Schema Updates**
   - Added a new `mun_onboarding_data` table to store MUN-specific user data
   - Ensured chat tables are properly set up with proper RLS policies
   - Added metadata field to messages table for potential experiments

2. **New Components and Context**
   - Created a `MUNOnboardingContext` to manage MUN-specific data
   - Developed a dedicated `MUNOnboardingModal` for collecting MUN conference details
   - Simplified the AI chat interface to focus on position paper writing directly in chat

3. **Chat System Simplification**
   - Removed canvas features from the position paper writing process
   - Set up direct chat-based writing similar to ChatGPT
   - Implemented Supabase integration for reliable chat storage
   - Added UUID generation for chat and message IDs

4. **Testing Infrastructure**
   - Added scripts for running the application on a specific port (3000)
   - Created a kill-servers.sh script to manage running instances
   - Set up easy access to test data through the MUN onboarding modal

## Using the Simplified Chat Component

1. **Starting the Testing Platform**
   ```
   # First, kill any existing server instances
   ./kill-servers.sh
   
   # Start the testing platform
   npm run test-platform
   ```

2. **Setup Process**
   - Navigate to http://localhost:3000/chat
   - Click the "Setup MUN Position" button in the top-right corner
   - Fill in the required information or use the "Fill with Test Data" button for quick testing
   - Complete the 3-step wizard to save your MUN position details

3. **Writing Position Papers**
   - All interactions happen directly in the chat interface
   - Type "write a position paper" to generate a complete draft
   - Ask for research, specific sections, or revisions as needed
   - All chat history is automatically saved to Supabase

## Modifying Key Variables for Testing

### 1. Onboarding Data
- **Method 1**: Use the MUN onboarding modal and "Fill with Test Data" button
- **Method 2**: Directly modify the `defaultMUNData` in `src/lib/mun-onboarding-context.tsx`
- **Method 3**: Update database values through Supabase dashboard for the `mun_onboarding_data` table

### 2. Request Data (Chat Input)
- Different chat inputs will trigger different response templates
- Key phrases like "write position paper" or "research" can be used
- All user inputs are saved to the Supabase messages table with the user's role

### 3. API Prompts
- Currently using mock responses in the `generateMockResponse` function
- To experiment with different templates, modify the function in `src/components/ai-chat-interface.tsx`
- For real API integration, replace the mock function with actual API calls

## Limitations and Considerations

1. **Mock Responses**
   - The current implementation uses mock responses for demonstration
   - Real API integration would require modifying the `processUserInput` function

2. **Database Dependencies**
   - The system requires Supabase to be running for chat history to work
   - Make sure to run `npm run init-db` if setting up for the first time

3. **Restart Process**
   - If you need to restart the frontend, use `./kill-servers.sh` to ensure clean restarts
   - The backend can continue running unless schema changes are made

4. **Error Handling**
   - The chat will continue working even if message saving fails
   - Check console logs for any Supabase connection issues

## Next Steps for Experimentation

1. Replace mock responses with real API calls
2. Experiment with different prompt formats
3. Enhance the metadata field in the messages table for tracking experiments
4. Add a feedback mechanism to rate and improve responses 