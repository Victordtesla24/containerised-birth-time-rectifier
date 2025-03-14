// @ts-ignore - Suppress the module resolution error
import { withIronSessionApiRoute, withIronSessionSsr } from 'iron-session/next';
// @ts-ignore - Suppress Next.js type errors
import { NextApiHandler, GetServerSidePropsContext, GetServerSidePropsResult } from 'next';

// Session configuration
const sessionConfig = {
  password: process.env.SESSION_SECRET || 'complex_password_at_least_32_characters_long',
  cookieName: 'birth-time-rectifier-session',
  cookieOptions: {
    secure: process.env.NODE_ENV === 'production',
    maxAge: 60 * 60 * 24, // 1 day
    httpOnly: true,
    sameSite: 'strict' as const,
  },
};

// Remove the duplicate declaration that conflicts with globals.d.ts
// The app-specific session properties are now handled in globals.d.ts

/**
 * Wrap an API route with Iron Session
 */
export function withSessionRoute(handler: NextApiHandler) {
  return withIronSessionApiRoute(handler, sessionConfig);
}

/**
 * Wrap getServerSideProps with Iron Session
 */
export function withSessionSsr<P extends { [key: string]: any } = { [key: string]: any }>(
  handler: (
    context: GetServerSidePropsContext,
  ) => GetServerSidePropsResult<P> | Promise<GetServerSidePropsResult<P>>,
) {
  return withIronSessionSsr(handler, sessionConfig);
}
