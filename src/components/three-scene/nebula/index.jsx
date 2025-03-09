import React, { useRef, useMemo, useState, useEffect } from 'react';
import { useFrame, useThree } from '@react-three/fiber';
import * as THREE from 'three';
import NebulaMaterial from './NebulaMaterial';
import TextureLoader from '../utils/TextureLoader';

/**
 * Main index file for Nebula components
 * Exports the Nebula component as the default export
 */
export { default as NebulaMaterial } from './NebulaMaterial';
export { default as NebulaShaders } from './NebulaShaders';

// Export the main Nebula component as default
export { default } from './Nebula';
