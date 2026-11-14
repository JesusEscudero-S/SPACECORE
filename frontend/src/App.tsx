import './App.css'
import Buscador from './components/busqueda/Buscador'
import PanelInfo from './components/busqueda/PanelInfo'
import Reproductor from './components/visor/Reproductor'
import VistaAladin from './components/visor/VistaAladin'

// Esqueleto inicial (T03). El layout real de la página se hace en la tarea T40 (rol #1).
function App() {
  return (
    <>
      <h1>SPACECORE</h1>
      <Buscador />
      <Reproductor />
      <PanelInfo />
      <VistaAladin />
    </>
  )
}

export default App
