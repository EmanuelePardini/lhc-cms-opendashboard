export const fmt = (v, d = 2) =>
  typeof v === "number" ? v.toFixed(d) : "—";

export const recoTypeLabel = t =>
  ({ G: "Global", T: "Tracker", S: "StandAlone" }[t] ?? t);

export function describeEvent(ev) {
  if (!ev) return null;
  const m = ev.invariant_mass;
  if (ev.z_candidate)       return { tag: "Z Boson candidate",   color: "#ffd700", desc: "This collision likely produced a Z boson — a force-carrying particle that mediates the weak nuclear force. It decayed almost instantly into two muons before we could detect it directly." };
  if (m > 3    && m < 3.2)  return { tag: "J/ψ candidate",       color: "#f97316", desc: "A possible J/psi meson — the particle whose 1974 discovery proved the existence of the charm quark. A landmark moment in particle physics." };
  if (m > 8.5  && m < 10.5) return { tag: "Υ (Upsilon) region",  color: "#34d399", desc: "This mass range corresponds to Upsilon mesons — bound states of a bottom quark and its antiparticle, orbiting each other like a tiny atom." };
  if (m < 1.2)               return { tag: "ρ/ω meson region",    color: "#c084fc", desc: "Very low-mass dimuon pair. Likely from rho or omega mesons — short-lived composite particles made of up and down quarks." };
  return                            { tag: "Dimuon pair",          color: "#00c8ff", desc: "Two muons flying in opposite directions from the collision point. By measuring their combined energy and momentum, scientists can reconstruct which particle created them." };
}