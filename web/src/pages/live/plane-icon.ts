/** Top-down airliner silhouette (white, nose up); mask:true lets deck.gl tint it per aircraft. */
const SVG =
  '<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 64 64"><path fill="#fff" d="M32 2c2.4 0 4 3.6 4 8v14l24 14v6l-24-7v13l6 5v4l-10-3-10 3v-4l6-5V37L4 44v-6l24-14V10c0-4.4 1.6-8 4-8z"/></svg>'
export const PLANE_ATLAS = 'data:image/svg+xml;base64,' + btoa(SVG)
export const PLANE_MAPPING = { plane: { x: 0, y: 0, width: 64, height: 64, anchorX: 32, anchorY: 32, mask: true } }
