// DEV/TEST ONLY — delete this whole folder before merging to main.
// Real platform format sizes for quick testing. The app loads this folder via
// import.meta.glob, so deleting it just removes the preset chips; custom
// width/height entry and drag-to-resize keep working.

export default [
  { name: 'Instagram Post', group: 'Social', width: 1080, height: 1080 },
  { name: 'Instagram Portrait', group: 'Social', width: 1080, height: 1350 },
  { name: 'Instagram Story', group: 'Social', width: 1080, height: 1920 },
  { name: 'Pinterest Pin', group: 'Social', width: 1000, height: 1500 },
  { name: 'X Post', group: 'Social', width: 1600, height: 900 },
  { name: 'LinkedIn Banner', group: 'Social', width: 1584, height: 396 },
  { name: 'YouTube Thumbnail', group: 'Video', width: 1280, height: 720 },
  { name: 'Full HD', group: 'Video', width: 1920, height: 1080 },
  { name: 'Leaderboard', group: 'Display ads', width: 728, height: 90 },
  { name: 'Billboard', group: 'Display ads', width: 970, height: 250 },
  { name: 'Medium Rectangle', group: 'Display ads', width: 300, height: 250 },
  { name: 'Wide Skyscraper', group: 'Display ads', width: 160, height: 600 },
]
