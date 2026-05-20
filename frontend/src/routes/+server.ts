import type { RequestHandler } from '@sveltejs/kit';

export const POST: RequestHandler = async () => {
    return new Response(null, {
        status: 200,
        headers: {
            // ⚠️ Name, Path and flags must be identical to the cookie created on login
            'Set-Cookie': 'token=; Path=/; HttpOnly; SameSite=Lax; Max-Age=0'
        }
    });
};