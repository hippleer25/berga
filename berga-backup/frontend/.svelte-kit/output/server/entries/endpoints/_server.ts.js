const POST = async () => {
  return new Response(null, {
    status: 200,
    headers: {
      // ⚠️ Nome, Path e flags devem ser idênticos ao cookie criado no login
      "Set-Cookie": "token=; Path=/; HttpOnly; SameSite=Lax; Max-Age=0"
    }
  });
};
export {
  POST
};
