# GUNI Robot Web Interface

## Overview

A modern web application built with Next.js 15 for managing and monitoring the GUNI Robot System. This interface provides user authentication, admin controls, and robot interaction capabilities.

## Technology Stack

- **Framework**: Next.js 15 with App Router
- **Language**: TypeScript
- **Styling**: Tailwind CSS 4
- **Authentication**: Clerk
- **Icons**: Lucide React
- **Deployment**: Vercel-ready

## Features

### 🔐 Authentication System
- **Clerk Integration**: Secure user authentication and management
- **Role-based Access**: Different interfaces for users and administrators
- **Session Management**: Persistent login sessions

### 👨‍💼 Admin Dashboard (`admin/`)
- Robot system monitoring and control
- User management and permissions
- System configuration and settings
- Analytics and usage statistics

### 👤 User Dashboard (`user-dashboard/`)
- Personal robot interaction interface
- Conversation history and preferences
- Voice and expression customization
- Personal settings management

### 🎨 Modern UI Components
- Responsive design for all device sizes
- Clean, intuitive interface design
- Real-time updates and notifications
- Accessible and user-friendly controls

## Project Structure

```
website/
├── README.md                    # This documentation
├── package.json                 # Dependencies and scripts
├── next.config.ts               # Next.js configuration
├── next-env.d.ts               # TypeScript environment types
├── tsconfig.json               # TypeScript configuration
├── postcss.config.mjs          # PostCSS configuration
├── eslint.config.mjs           # ESLint configuration
├── LICENSE                     # Website license
├── public/                     # Static assets
│   ├── file.svg               # File icon
│   ├── globe.svg              # Globe icon
│   ├── next.svg               # Next.js logo
│   ├── vercel.svg             # Vercel logo
│   └── window.svg             # Window icon
└── src/                       # Source code
    ├── middleware.ts          # Request middleware
    └── app/                   # App Router structure
        ├── favicon.ico        # Site favicon
        ├── globals.css        # Global styles
        ├── layout.tsx         # Root layout component
        ├── page.tsx           # Home page
        ├── (auth)/            # Authentication pages
        ├── admin/             # Admin dashboard pages
        ├── user-dashboard/    # User interface pages
        └── components/        # Shared React components
            └── ui/            # UI component library
```

## Quick Start

### Prerequisites

- Node.js 18+ 
- npm or yarn
- Clerk account (for authentication)

### Installation

```bash
# Clone and navigate to website directory
cd website/

# Install dependencies
npm install

# Set up environment variables
cp .env.local.example .env.local
# Edit .env.local with your Clerk keys

# Run development server
npm run dev
```

### Environment Variables

Create a `.env.local` file in the website root:

```env
# Clerk Authentication
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_your_key_here
CLERK_SECRET_KEY=sk_test_your_secret_key_here

# Clerk URLs
NEXT_PUBLIC_CLERK_SIGN_IN_URL=/sign-in
NEXT_PUBLIC_CLERK_SIGN_UP_URL=/sign-up
NEXT_PUBLIC_CLERK_AFTER_SIGN_IN_URL=/user-dashboard
NEXT_PUBLIC_CLERK_AFTER_SIGN_UP_URL=/user-dashboard

# Robot API Configuration
NEXT_PUBLIC_ROBOT_API_URL=http://localhost:8001


# Optional: Database URL for extended features
DATABASE_URL=your_database_url_here
```

### Development Commands

```bash
# Start development server
npm run dev

# Build for production
npm run build

# Start production server
npm run start

# Run linting
npm run lint
```

## Application Routes

### Public Routes
- `/` - Landing page and general information
- `/about` - About GUNI and the robot project
- `/contact` - Contact information and support

### Authentication Routes (`(auth)/`)
- `/sign-in` - User login page
- `/sign-up` - User registration page
- `/sign-out` - Logout confirmation

### User Routes (`user-dashboard/`)
- `/user-dashboard` - Main user interface
- `/user-dashboard/robot` - Robot interaction controls
- `/user-dashboard/conversations` - Conversation history
- `/user-dashboard/settings` - User preferences
- `/user-dashboard/help` - User help and documentation

### Admin Routes (`admin/`)
- `/admin` - Admin dashboard overview
- `/admin/robots` - Robot system management
- `/admin/users` - User management interface
- `/admin/settings` - System configuration
- `/admin/analytics` - Usage statistics and analytics
- `/admin/logs` - System logs and monitoring

## Component Architecture

### Layout System
- **Root Layout** (`layout.tsx`): Global layout with navigation and authentication
- **Route Groups**: Organized authentication and dashboard layouts
- **Middleware** (`middleware.ts`): Route protection and authentication checks

### Authentication Flow
```
User Access → Middleware Check → Clerk Authentication → Role-based Routing
                ↓
    Unauthenticated → Sign-in Page
                ↓
    User Role → User Dashboard
                ↓
    Admin Role → Admin Dashboard
```

### UI Components (`components/ui/`)
Reusable UI components built with Tailwind CSS:
- Buttons, forms, and input components
- Modal and dialog systems
- Navigation and menu components
- Cards and layout containers
- Loading and status indicators

## Integration with Robot System

### API Communication
The web interface communicates with the robot system through:

```typescript
// Example API integration
const robotAPI = {
  baseURL: process.env.NEXT_PUBLIC_ROBOT_API_URL,
  
  // Send command to robot
  sendCommand: async (command: string) => {
    const response = await fetch(`${robotAPI.baseURL}/api/command`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ command })
    });
    return response.json();
  },
  
  // Get robot status
  getStatus: async () => {
    const response = await fetch(`${robotAPI.baseURL}/api/status`);
    return response.json();
  },
  
  // Get conversation history
  getConversations: async (userId: string) => {
    const response = await fetch(`${robotAPI.baseURL}/api/conversations/${userId}`);
    return response.json();
  }
};
```

### Real-time Features
- WebSocket connections for live robot status
- Server-sent events for conversation updates
- Real-time expression and mood changes
- Live audio stream controls

## Deployment

### Vercel (Recommended)

```bash
# Install Vercel CLI
npm install -g vercel

# Deploy to Vercel
vercel

# Set environment variables in Vercel dashboard
```

### Alternative Deployment

```bash
# Build the application
npm run build

# Deploy the .next folder to your hosting provider
# Ensure Node.js 18+ runtime support
```

### Environment Setup for Production

1. **Clerk Configuration**:
   - Set up production Clerk application
   - Configure domain and redirect URLs
   - Update environment variables

2. **Robot API Integration**:
   - Ensure robot API server is accessible
   - Configure CORS for web domain
   - Set up proper authentication

3. **Database Setup** (if using extended features):
   - Set up production database
   - Configure connection strings
   - Run database migrations

## Development Guidelines

### Code Structure
- Use TypeScript for all components and utilities
- Follow Next.js App Router conventions
- Implement proper error boundaries
- Use server components where appropriate

### Styling
- Tailwind CSS for all styling
- Consistent component design system
- Responsive design for all screen sizes
- Dark mode support (future enhancement)

### State Management
- React state for component-level state
- Context API for global app state
- Server state management for API data
- Local storage for user preferences

### Testing
```bash
# Add testing dependencies
npm install --save-dev @testing-library/react @testing-library/jest-dom jest

# Run tests
npm run test
```

## Features Roadmap

### Current Version (v0.1.0)
✅ Basic authentication with Clerk  
✅ User and admin dashboard layouts  
✅ Robot API integration setup  
✅ Responsive design foundation  

### Planned Features (v0.2.0)
🔄 Real-time robot control interface  
🔄 Conversation history viewer  
🔄 Expression and mood controls  
🔄 User preference management  

### Future Enhancements (v1.0.0)
📋 Advanced analytics dashboard  
📋 Multi-robot support  
📋 Mobile app integration  
📋 Voice command web interface  
📋 AI training data management  

## Troubleshooting

### Common Issues

1. **Authentication not working**:
   ```bash
   # Check Clerk configuration
   # Verify environment variables
   # Check Clerk dashboard settings
   ```

2. **Build errors**:
   ```bash
   # Clear Next.js cache
   rm -rf .next
   npm run build
   ```

3. **Styling issues**:
   ```bash
   # Rebuild Tailwind
   npm run dev
   # Check for conflicting CSS
   ```

4. **API connection issues**:
   - Verify robot server is running
   - Check CORS configuration
   - Validate API URL in environment variables

### Development Tips

- Use Next.js development tools for debugging
- Enable TypeScript strict mode for better error catching
- Use React Developer Tools for component debugging
- Test on multiple browsers and devices

## Contributing

### Development Workflow
1. Create feature branch from main
2. Implement feature with proper TypeScript types
3. Add appropriate documentation
4. Test on multiple screen sizes
5. Submit pull request with description

### Code Standards
- Follow TypeScript best practices
- Use consistent naming conventions
- Add proper JSDoc comments
- Implement proper error handling
- Write responsive, accessible code

## API Documentation

### Robot Control Endpoints
- `POST /api/robot/command` - Send command to robot
- `GET /api/robot/status` - Get current robot status
- `POST /api/robot/expression` - Change robot expression
- `GET /api/robot/conversations` - Get conversation history

### User Management Endpoints
- `GET /api/users` - List users (admin only)
- `POST /api/users` - Create user (admin only)
- `PUT /api/users/:id` - Update user
- `DELETE /api/users/:id` - Delete user (admin only)

---

**Version**: 0.1.0  
**Last Updated**: July 1, 2025  
**Framework**: Next.js 15  
**Status**: Active Development  
**License**: See LICENSE file
