// Small wrapper around fetch(). Every call goes to the FastAPI backend through the Vite proxy (/api).
async function request(path, options) {
  let response;
  try {
    response = await fetch(path, options);
  } catch {
    throw { network: true };
  }
  if (!response.ok) {
    let detail = null;
    try {
      detail = (await response.json()).detail;
    } catch {
      /* ignore */
    }
    throw { status: response.status, detail };
  }
  return response.json();
}

export const getStats = () => request("/api/stats");
export const getDemoCases = () => request("/api/demo-cases");
export const listRegistrations = () => request("/api/registrations");
export const getRegistration = (ref) => request(`/api/registrations/${encodeURIComponent(ref)}`);
export const submitRegistration = (form) =>
  request("/api/registrations", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(form),
  });
