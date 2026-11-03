/**
 * The shapes photos are cropped to before upload, matched to where each is
 * shown: a logo is square, a shop cover is a wide banner, a product or
 * gallery photo defaults to 4:3 with square and wide as choices. A product's
 * extra photos are not cropped: its gallery shows each photo whole.
 */
export const LOGO_ASPECT = 1
export const COVER_ASPECT = 3
export const PHOTO_ASPECT = 4 / 3
export const PHOTO_RATIOS = [4 / 3, 1, 16 / 9]
export const REEL_ASPECT = 9 / 16
