import { css } from "../color.js";
import { esc } from "../format.js";
import { isCapital } from "../world.js";
import { yieldGrid, amenities, industries, gdpRow, popLine, growthSpan, showPanel, hidePanel } from "./infoPanel.js";

/**
 * ctx: {w, nation, onClose, onPedia, onState(stateIndex)}
 */
export function openCityPanel(city, ctx) {
  const { w, nation } = ctx;
  const n = nation.nation;
  const owner = city.cell != null ? w.raw.owner[city.cell] : -1;
  const col = css(w.stateColor[owner] || [190, 190, 190]);

  // The city's states as links to their state panels.
  const main = city.state_main || (city.states || [])[0];
  const si = w.raw.states.findIndex((s) => s.abbr === main);
  const states = si >= 0
    ? (ctx.onState
        ? `<button class="chip" data-state="${si}" title="Ouvrir ${esc(w.raw.states[si].name)}">${esc(w.raw.states[si].name)}</button>`
        : `<span class="chip">${esc(w.raw.states[si].name)}</span>`)
    : "";

  const growth = growthSpan(city, n);

  showPanel({
    kind: "city",
    stripe: col,
    title: city.name,
    titleHtml: `${isCapital(city) ? `<span class="cap" title="Capitale nationale">★</span> ` : ""}${esc(city.name)}`,
    sub: `${esc(city.full || "")}${states ? `<div class="chips">${states}</div>` : ""}`,
    headExtra: popLine(city, growth),
    sections: [
      { title: "Rendements", html: `<div class="yield-grid">${yieldGrid(nation, city.yields)}</div>` },
      { title: "Cadre de vie &amp; logement", html: amenities(city, n) + gdpRow(city) },
      { title: "Quartiers · où l'on travaille", html: industries(city, nation) },
    ],
    foot: `Source : ${esc(nation.vintage)}${nation.gdp_vintage ? ` ; PIB : ${esc(nation.gdp_vintage)}` : ""}.
      Vert ×N = la part de ce secteur dans l'emploi local vaut N fois la moyenne nationale.`,
    onClose: ctx.onClose,
    onPedia: ctx.onPedia,
    wire(panel) {
      panel.querySelectorAll("[data-state]").forEach((b) => (b.onclick = () => ctx.onState(+b.dataset.state)));
    },
  });
}

export const closeCityPanel = hidePanel;
