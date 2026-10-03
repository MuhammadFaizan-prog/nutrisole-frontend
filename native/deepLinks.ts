export function routeFromURL<T extends string>(url: string | null, screens: readonly T[]): T | null {
  if (!url) return null;
  try {
    const match = /^nutrisole:\/\/(?:screens\/)?([^/?#]+)(?:[?#].*)?$/i.exec(url);
    if (!match) return null;
    const screen = decodeURIComponent(match[1]);
    return screens.includes(screen as T) ? screen as T : null;
  } catch {
    return null;
  }
}
