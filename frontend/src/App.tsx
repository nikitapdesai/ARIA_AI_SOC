import { lazy, Suspense } from "react";
import { Route, Routes } from "react-router-dom";
import Layout from "./components/Layout";
import PageSkeleton from "./components/skeletons/PageSkeleton";

const Overview = lazy(() => import("./pages/Overview"));
const AlertQueue = lazy(() => import("./pages/AlertQueue"));
const AlertDetail = lazy(() => import("./pages/AlertDetail"));
const Analytics = lazy(() => import("./pages/Analytics"));
const LiveAnalyze = lazy(() => import("./pages/LiveAnalyze"));
const Incidents = lazy(() => import("./pages/Incidents"));
const KnowledgeBase = lazy(() => import("./pages/KnowledgeBase"));

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<Suspense fallback={<PageSkeleton />}><Overview /></Suspense>} />
        <Route path="alerts" element={<Suspense fallback={<PageSkeleton />}><AlertQueue /></Suspense>} />
        <Route path="alerts/:alertId" element={<Suspense fallback={<PageSkeleton />}><AlertDetail /></Suspense>} />
        <Route path="analytics" element={<Suspense fallback={<PageSkeleton />}><Analytics /></Suspense>} />
        <Route path="live" element={<Suspense fallback={<PageSkeleton />}><LiveAnalyze /></Suspense>} />
        <Route path="incidents" element={<Suspense fallback={<PageSkeleton />}><Incidents /></Suspense>} />
        <Route path="knowledge-base" element={<Suspense fallback={<PageSkeleton />}><KnowledgeBase /></Suspense>} />
      </Route>
    </Routes>
  );
}
