// Currently we import the following files textually as part of our `npm run build script`;
// we can do this because both files are distributed as iife scripts. If we wanted to use
// something like rollup in the future we could do so however using the es6 module syntax below.
//
// import * as GOVUKFrontend from 'govuk-frontend/govuk/all.js';
// import * as DMGOVUKFrontend from 'digitalmarketplace-govuk-frontend/digitalmarketplace/all.js';

GOVUKFrontend.initAll();
DMGOVUKFrontend.initAll();
