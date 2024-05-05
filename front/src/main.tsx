import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.tsx'
import './index.css'


// import {createBrowserRouter, RouterProvider} from "react-router-dom";

import '../i18n/configs'

// import Top from './pages/Top'
// import Page404 from "./pages/404.tsx";
//
// const router = createBrowserRouter([
//   {
//     path: "/",
//     element: <Top/>
//   },
//   {
//     path: "*",
//     element: <Page404/>
//   }
// ]);

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App/>
    {/* <RouterProvider router={router}/> */}
  </React.StrictMode>,
)
