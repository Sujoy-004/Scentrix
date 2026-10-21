import type { NextConfig } from "next";

// Wires the dev server up to the Cloudflare Workers runtime so local `next
// dev` and the deployed worker behave the same. Development only - a
// production build must not depend on the wrangler platform proxy.
if (process.env.NODE_ENV === "development") {
  import("@opennextjs/cloudflare").then((m) => m.initOpenNextCloudflareForDev());
}

const nextConfig: NextConfig = {
  // Dev-only. Lets other devices on the LAN load HMR + the geist webfont
  // (otherwise both are blocked and the page renders with fallback fonts).
  // 172.16.0.x comes from DHCP — update this if the machine's LAN IP changes.
  allowedDevOrigins: ["127.0.0.1", "localhost", "172.16.0.2"],
  async redirects() {
    return [
      {
        source: '/onboarding/quiz',
        destination: '/quiz',
        permanent: true,
      },
    ];
  },
};

export default nextConfig;
