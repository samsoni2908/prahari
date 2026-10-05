/** @type {import('next').NextConfig} */
// Keep one config authority, including the API proxy and standalone build.
module.exports = async () => (await import("./next.config.mjs")).default;
