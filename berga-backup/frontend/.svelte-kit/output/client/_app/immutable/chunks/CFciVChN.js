import{T as a,J as c}from"./mRmwuoWL.js";function l(e,n,i){a(()=>{var t=c(()=>n(e,i?.())||{});if(t?.destroy)return()=>t.destroy()})}function p(e){function n(i){const t=document.createElement("span"),r=e.getBoundingClientRect(),o=Math.max(r.width,r.height);t.style.cssText=`
			position:absolute;border-radius:50%;pointer-events:none;
			width:${o}px;height:${o}px;
			left:${i.clientX-r.left-o/2}px;
			top:${i.clientY-r.top-o/2}px;
			background:color-mix(in oklch, var(--color-base-content) 12%, transparent);
			transform:scale(0);opacity:1;
			animation:ripple-anim 480ms cubic-bezier(0.4,0,0.2,1) forwards;
		`,e.appendChild(t),t.addEventListener("animationend",()=>t.remove())}return e.addEventListener("click",n),{destroy:()=>e.removeEventListener("click",n)}}export{l as a,p as r};
