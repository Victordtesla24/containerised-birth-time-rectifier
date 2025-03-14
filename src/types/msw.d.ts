// Type declarations for MSW (Mock Service Worker)
declare module 'msw/node' {
  import { RequestHandler, RestHandler } from 'msw';

  export interface SetupServerApi {
    listen(options?: { onUnhandledRequest?: 'error' | 'warn' | 'bypass' }): void;
    close(): void;
    resetHandlers(...handlers: RequestHandler[]): void;
    use(...handlers: RequestHandler[]): void;
  }

  export function setupServer(...handlers: RestHandler[]): SetupServerApi;
}

declare module 'msw/browser' {
  import { RequestHandler, RestHandler } from 'msw';

  export interface SetupWorkerApi {
    start(options?: { onUnhandledRequest?: 'error' | 'warn' | 'bypass' }): void;
    stop(): void;
    resetHandlers(...handlers: RequestHandler[]): void;
    use(...handlers: RequestHandler[]): void;
  }

  export function setupWorker(...handlers: RestHandler[]): SetupWorkerApi;
}

declare module 'msw' {
  export type DefaultBodyType = Record<string, any> | string | number | boolean | null;

  export interface PathParams<Key extends string = string> {
    [key: string]: string;
  }

  export interface ResponseTransformer {
    (response: Response): Response;
  }

  export interface ResponseComposition {
    (handler1: ResponseTransformer, handler2: ResponseTransformer, ...handlers: ResponseTransformer[]): Response;
  }

  export interface ResponseResolver<
    RequestBodyType = DefaultBodyType,
    Params extends PathParams = PathParams,
    ResponseBodyType = DefaultBodyType
  > {
    (
      req: {
        body: RequestBodyType;
        params: Params;
        cookies: Record<string, string>;
        headers: Record<string, string>;
      },
      res: ResponseComposition,
      ctx: {
        status: (statusCode: number) => ResponseTransformer;
        json: <T>(body: T) => ResponseTransformer;
        text: (body: string) => ResponseTransformer;
        xml: (body: string) => ResponseTransformer;
        delay: (ms: number) => ResponseTransformer;
        set: (name: string, value: string) => ResponseTransformer;
      }
    ): Response | Promise<Response>;
  }

  export type RequestHandler = RestHandler;

  export type RestHandler = {
    /**
     * Request handler for the "rest" API.
     */
    operation: string;
  };

  export const rest: {
    get: <RequestBodyType extends DefaultBodyType = DefaultBodyType, Params extends PathParams<keyof Params> = PathParams<string>, ResponseBodyType extends DefaultBodyType = DefaultBodyType>(path: string, resolver: ResponseResolver<RequestBodyType, Params, ResponseBodyType>) => RestHandler;
    post: <RequestBodyType extends DefaultBodyType = DefaultBodyType, Params extends PathParams<keyof Params> = PathParams<string>, ResponseBodyType extends DefaultBodyType = DefaultBodyType>(path: string, resolver: ResponseResolver<RequestBodyType, Params, ResponseBodyType>) => RestHandler;
    put: <RequestBodyType extends DefaultBodyType = DefaultBodyType, Params extends PathParams<keyof Params> = PathParams<string>, ResponseBodyType extends DefaultBodyType = DefaultBodyType>(path: string, resolver: ResponseResolver<RequestBodyType, Params, ResponseBodyType>) => RestHandler;
    delete: <RequestBodyType extends DefaultBodyType = DefaultBodyType, Params extends PathParams<keyof Params> = PathParams<string>, ResponseBodyType extends DefaultBodyType = DefaultBodyType>(path: string, resolver: ResponseResolver<RequestBodyType, Params, ResponseBodyType>) => RestHandler;
    patch: <RequestBodyType extends DefaultBodyType = DefaultBodyType, Params extends PathParams<keyof Params> = PathParams<string>, ResponseBodyType extends DefaultBodyType = DefaultBodyType>(path: string, resolver: ResponseResolver<RequestBodyType, Params, ResponseBodyType>) => RestHandler;
    options: <RequestBodyType extends DefaultBodyType = DefaultBodyType, Params extends PathParams<keyof Params> = PathParams<string>, ResponseBodyType extends DefaultBodyType = DefaultBodyType>(path: string, resolver: ResponseResolver<RequestBodyType, Params, ResponseBodyType>) => RestHandler;
    head: <RequestBodyType extends DefaultBodyType = DefaultBodyType, Params extends PathParams<keyof Params> = PathParams<string>, ResponseBodyType extends DefaultBodyType = DefaultBodyType>(path: string, resolver: ResponseResolver<RequestBodyType, Params, ResponseBodyType>) => RestHandler;
  };
}
