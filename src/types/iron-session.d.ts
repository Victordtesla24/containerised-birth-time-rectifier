import { NextApiHandler, NextApiRequest, NextApiResponse } from 'next';
import { GetServerSidePropsContext, GetServerSidePropsResult } from 'next';

declare module 'iron-session/next' {
  export interface IronSessionOptions {
    cookieName: string;
    password: string;
    cookieOptions?: {
      secure?: boolean;
      httpOnly?: boolean;
      sameSite?: 'strict' | 'lax' | 'none';
      path?: string;
      domain?: string;
      maxAge?: number;
    };
    ttl?: number;
  }

  export function withIronSessionApiRoute<T>(
    handler: NextApiHandler<T>,
    options: IronSessionOptions
  ): NextApiHandler<T>;

  export function withIronSessionSsr<
    P extends { [key: string]: unknown } = { [key: string]: unknown },
  >(
    handler: (
      context: GetServerSidePropsContext,
    ) => GetServerSidePropsResult<P> | Promise<GetServerSidePropsResult<P>>,
    options: IronSessionOptions,
  ): (
    context: GetServerSidePropsContext,
  ) => Promise<GetServerSidePropsResult<P>>;

  // Add session property to Next.js API request
  declare module 'next' {
    interface NextApiRequest {
      session: {
        [key: string]: any;
        save(): Promise<void>;
        destroy(): Promise<void>;
      };
    }
  }
}

declare module 'next' {
  interface NextApiRequest {
    session: {
      [key: string]: any;
    };
  }
}
