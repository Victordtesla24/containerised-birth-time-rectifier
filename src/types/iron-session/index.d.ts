import { NextApiHandler, NextApiRequest } from 'next';
import { GetServerSidePropsContext, GetServerSidePropsResult } from 'next';

// Main module declaration
declare module 'iron-session' {
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

  export function sealData(data: any, options: IronSessionOptions): Promise<string>;
  export function unsealData(seal: string, options: IronSessionOptions): Promise<any>;
}

// Next.js integration
declare module 'iron-session/next' {
  import { IronSessionOptions } from 'iron-session';

  export { IronSessionOptions };

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
}

// Extend Next.js types
declare module 'next' {
  interface NextApiRequest {
    session: {
      [key: string]: any;
      save(): Promise<void>;
      destroy(): Promise<void>;
    };
  }
}
