import React from 'react';

/**
 * BrandMark – renders the Ile Ubuntu app logo.
 * Usage: <BrandMark className="w-6 h-6 object-contain" />
 */
const BrandMark = ({ className = '', alt = 'Ile Ubuntu', ...props }) => (
  <img
    src="/icon-512.png"
    alt={alt}
    className={className}
    {...props}
  />
);

export default BrandMark;
