# MUN Connect Deployment Checklist

## Project Structure

✅ Confirm the separation of applications:
- Static Marketing Site (`munconnect.vercel.app`)
- Dashboard Application (`dashboard.munconnect.vercel.app`)

## Configuration Files

✅ Verify proper configuration:
- `vercel.json` - For the main marketing site
- `vercel-dashboard.json` - For the dashboard application

## Code Changes

✅ Homepage Changes:
- Remove authentication state checks from the landing page
- Replace conditional Dashboard/Profile buttons with permanent Login/Register buttons
- Ensure all dashboard links point to the dashboard subdomain

✅ Auth Context Changes:
- Main site: No AuthProvider in the root layout
- Dashboard: AuthProvider only wraps dashboard routes

✅ Middleware Changes:
- Ensure middleware is configured to handle auth routes correctly
- Confirm protected routes redirect to login when unauthenticated
- Ensure auth routes don't create redirect loops

## Deployment Steps

### Main Marketing Site

1. [ ] Create a new Vercel project
2. [ ] Set project name: `mun-connect`
3. [ ] Choose the main GitHub repository
4. [ ] Configure build settings:
   - [ ] Build command: `npm run build`
   - [ ] Output directory: `.next`
   - [ ] Configuration file: `vercel.json`
5. [ ] Set environment variables:
   - [ ] Link `@next_public_supabase_url`
   - [ ] Link `@next_public_supabase_anon_key`
6. [ ] Configure custom domain: `munconnect.vercel.app`
7. [ ] Deploy the project

### Dashboard Application

1. [ ] Create a new Vercel project
2. [ ] Set project name: `mun-connect-dashboard`
3. [ ] Choose the same GitHub repository
4. [ ] Configure build settings:
   - [ ] Build command: `npm run build`
   - [ ] Output directory: `.next`
   - [ ] Configuration file: `vercel-dashboard.json`
5. [ ] Set environment variables:
   - [ ] Link `@next_public_supabase_url`
   - [ ] Link `@next_public_supabase_anon_key`
6. [ ] Configure custom domain: `dashboard.munconnect.vercel.app`
7. [ ] Deploy the project

## Testing Checklist

- [ ] Verify main site loads with Login/Register buttons
- [ ] Test Login button redirects to dashboard login page
- [ ] Test Register button redirects to dashboard register page
- [ ] Confirm successful login keeps user on dashboard site
- [ ] Test session persistence within dashboard site
- [ ] Verify protected routes require authentication
- [ ] Test profile completion redirect works correctly
- [ ] Ensure sign-out properly clears session
- [ ] Test direct URL access to dashboard routes

## Potential Issues to Watch For

- CORS errors when making cross-domain API calls
- Cookie domain issues affecting auth state
- Redirect loops if middleware is misconfigured
- Environment variable mismatches between projects
- URL rewrite issues for dashboard paths
