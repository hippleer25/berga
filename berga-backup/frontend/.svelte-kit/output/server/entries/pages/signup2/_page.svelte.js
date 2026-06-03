import { c as attr } from "../../../chunks/index2.js";
import { U as User } from "../../../chunks/user.js";
import { C as Circle_user } from "../../../chunks/circle-user.js";
import { M as Mail, L as Lock, E as Eye } from "../../../chunks/mail.js";
function _page($$renderer) {
  let username = "";
  let password = "";
  let full_name = "";
  let email = "";
  let loading = false;
  $$renderer.push(`<div class="min-h-screen flex items-center justify-center bg-base-200 px-6"><div class="w-full max-w-lg bg-base-100 rounded-2xl shadow-xl overflow-hidden pt-5"><div class="px-10 py-10 max-w-md mx-auto space-y-6"><h1 class="text-3xl font-semibold">Sign up</h1> <p>You are creating a Berga account</p> <div><label for="username" class="font-medium block mb-2">Account</label> <div class="relative flex items-center"><span class="input-icon absolute left-3 z-10 text-primary pointer-events-none">`);
  User($$renderer, { size: 18, color: "currentColor" });
  $$renderer.push(`<!----></span> <input id="username" type="text" placeholder="Enter your username" class="input bg-base-200 border-none w-full pl-10 focus:outline-none"${attr("value", username)}/></div></div> <div><label for="full_name" class="font-medium block mb-2">Full name</label> <div class="relative flex items-center"><span class="input-icon absolute left-3 z-10 text-primary pointer-events-none">`);
  Circle_user($$renderer, { size: 18, color: "currentColor" });
  $$renderer.push(`<!----></span> <input id="full_name" type="text" placeholder="Enter your full name" class="input bg-base-200 border-none w-full pl-10 focus:outline-none"${attr("value", full_name)}/></div></div> <div><label for="email" class="font-medium block mb-2">Email</label> <div class="relative flex items-center"><span class="input-icon absolute left-3 z-10 text-primary pointer-events-none">`);
  Mail($$renderer, { size: 18, color: "currentColor" });
  $$renderer.push(`<!----></span> <input id="email" type="email" placeholder="Enter your email" class="input bg-base-200 border-none w-full pl-10 focus:outline-none"${attr("value", email)}/></div></div> <div><label for="password" class="font-medium block mb-2">Password</label> <div class="relative flex items-center"><span class="input-icon absolute left-3 z-10 text-primary pointer-events-none">`);
  Lock($$renderer, { size: 18, color: "currentColor" });
  $$renderer.push(`<!----></span> <input id="password"${attr("type", "password")} placeholder="Enter your password" class="input bg-base-200 border-none w-full pl-10 pr-10 focus:outline-none"${attr("value", password)}/> <button type="button" class="absolute right-3 z-10 text-primary">`);
  {
    $$renderer.push("<!--[!-->");
    Eye($$renderer, { size: 18 });
  }
  $$renderer.push(`<!--]--></button></div></div> `);
  {
    $$renderer.push("<!--[!-->");
  }
  $$renderer.push(`<!--]--> <div class="flex justify-between items-center pt-10"><button class="btn bg-base-200 hover:bg-base-300 border-none text-base-content">Back</button> <button class="btn btn-primary border-none font-bold px-7"${attr("disabled", loading, true)}>`);
  {
    $$renderer.push("<!--[!-->");
    $$renderer.push(`Done`);
  }
  $$renderer.push(`<!--]--></button></div></div></div></div>`);
}
export {
  _page as default
};
