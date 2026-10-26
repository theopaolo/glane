// Reçoit le formulaire /proposer/ et lance .github/workflows/proposition.yml.
// GITHUB_TOKEN : jeton à grain fin limité au dépôt glane, permission « Actions : read and write ».
const PAGE = "https://glane.ludique.dev/proposer/";
const DISPATCH = "https://api.github.com/repos/theopaolo/glane/actions/workflows/proposition.yml/dispatches";

export default {
  async fetch(request, env) {
    if (request.method !== "POST") return Response.redirect(PAGE, 303);
    const form = await request.formData();
    // Champ piège caché : seuls les robots le remplissent. Ils reçoivent la même réponse qu'un envoi réussi.
    if (form.get("site")) return Response.redirect(PAGE + "#merci", 303);
    const payload = JSON.stringify({
      titre: form.get("titre"),
      url: form.get("url"),
      categorie: form.get("categorie"),
      francophone: form.has("francophone"),
      tags: form.getAll("tags"),
      description: form.get("description"),
      pseudo: form.get("pseudo"),
      github: form.get("github"),
      site_perso: form.get("site_perso"),
    });
    const response = await fetch(DISPATCH, {
      method: "POST",
      headers: {
        Accept: "application/vnd.github+json",
        Authorization: `Bearer ${env.GITHUB_TOKEN}`,
        "User-Agent": "glane-proposition",
      },
      body: JSON.stringify({ ref: "main", inputs: { payload } }),
    });
    if (!response.ok) console.error(response.status, await response.text());
    return Response.redirect(PAGE + (response.ok ? "#merci" : "#erreur"), 303);
  },
};
