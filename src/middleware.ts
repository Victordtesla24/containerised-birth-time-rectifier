import { NextRequest, NextResponse } from 'next/server';

export const config = {
  matcher: '/api/:path*',
};

export function middleware(request: NextRequest) {
  // Continue to the next middleware/route handler
  // The main purpose is to keep connections alive longer
  return NextResponse.next();
}
