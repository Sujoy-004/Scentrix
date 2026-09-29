import type { NextConfig } from "next";

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
