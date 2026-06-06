import '@testing-library/jest-dom';
import { vi } from 'vitest';
import React from 'react';

// 1. Mock ResizeObserver
class ResizeObserverMock {
  observe() {}
  unobserve() {}
  disconnect() {}
}
global.ResizeObserver = ResizeObserverMock;

// 2. Mock React-Leaflet to bypass JSDOM rendering limits (JSX-free)
vi.mock('react-leaflet', () => {
  return {
    MapContainer: ({ children }: any) => React.createElement('div', { 'data-testid': 'mock-map' }, children),
    TileLayer: () => React.createElement('div', null),
    Marker: ({ children }: any) => React.createElement('div', null, children),
    Popup: ({ children }: any) => React.createElement('div', null, children),
    Polygon: () => React.createElement('div', null),
    GeoJSON: () => React.createElement('div', null),
    Circle: () => React.createElement('div', null),
    useMap: () => ({
      invalidateSize: vi.fn(),
      setView: vi.fn(),
      fitBounds: vi.fn(),
    }),
    useMapEvents: () => ({}),
  };
});