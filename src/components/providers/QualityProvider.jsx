/**
 * QualityProvider Component
 * A wrapper component that provides adaptive quality settings for WebGL rendering
 * based on device capabilities
 */
import React from 'react';
import PropTypes from 'prop-types';
import { QualityProvider as CoreQualityProvider } from '../three-scene/core/QualityContext';

/**
 * Application-level QualityProvider that wraps the core implementation
 */
export const QualityProvider = ({ children }) => {
  return <CoreQualityProvider>{children}</CoreQualityProvider>;
};

QualityProvider.propTypes = {
  children: PropTypes.node.isRequired
};

export default QualityProvider;
