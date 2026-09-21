import '@testing-library/jest-dom';
import { vi } from 'vitest';
import React from 'react';

// 1. Mock ResizeObserver
class ResizeObserverMock {
  observe() {}
  unobserve() {}
  disconnect() {}
}
globalThis.ResizeObserver = ResizeObserverMock;

// 2. Mock React-Leaflet to bypass JSDOM rendering limits (JSX-free)
type WithChildren = { children?: React.ReactNode };

vi.mock('react-leaflet', () => {
  return {
    MapContainer: ({ children }: WithChildren) =>
      React.createElement('div', { 'data-testid': 'mock-map' }, children),
    TileLayer: () => React.createElement('div', null),
    Marker: ({ children }: WithChildren) => React.createElement('div', null, children),
    Popup: ({ children }: WithChildren) => React.createElement('div', null, children),
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
