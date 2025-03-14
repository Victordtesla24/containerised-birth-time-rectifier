/// <reference types="next" />
/// <reference types="next/types/global" />
/// <reference types="next/image-types/global" />

// NOTE: This file should not be edited
// see https://nextjs.org/docs/basic-features/typescript for more information.

declare module 'next' {
  export type NextPage<P = {}, IP = P> = React.ComponentType<P> & {
    getInitialProps?(context: any): Promise<IP> | IP;
  };

  export interface NextApiRequest extends import('http').IncomingMessage {
    query: {
      [key: string]: string | string[];
    };
    cookies: {
      [key: string]: string;
    };
    body: any;
  }

  export interface NextApiResponse<T = any> extends import('http').ServerResponse {
    status(statusCode: number): NextApiResponse<T>;
    json(data: T): void;
    send(data: string | object | Buffer): void;
    redirect(statusOrUrl: number | string, url?: string): void;
    revalidate(urlPath: string): Promise<void>;
  }
}
