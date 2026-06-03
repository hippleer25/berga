import { redirect } from "@sveltejs/kit";
const load = () => {
  redirect(302, "/settings/appearance");
};
export {
  load
};
