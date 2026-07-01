import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { DataProvider } from './lib/data'
import { LightboxProvider } from './components/Lightbox'
import Home from './pages/Home'
import GenusDetail from './pages/GenusDetail'
import SpeciesDetail from './pages/SpeciesDetail'
import { AddObservation, Curiosity } from './pages/Other'
import FieldTrips from './pages/FieldTrips'
import ProposalFigures from './pages/ProposalFigures'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <DataProvider>
      <LightboxProvider>
      <BrowserRouter basename="/xena">
        <Routes>
          <Route path="/"              element={<Home />} />
          <Route path="/genus/:genus"  element={<GenusDetail />} />
          <Route path="/species/:taxonId" element={<SpeciesDetail />} />
          <Route path="/add"           element={<AddObservation />} />
          <Route path="/field-trips"   element={<FieldTrips />} />
          <Route path="/curiosity"     element={<Curiosity />} />
          <Route path="/proposals"     element={<ProposalFigures />} />
        </Routes>
      </BrowserRouter>
      </LightboxProvider>
    </DataProvider>
  </React.StrictMode>
)
