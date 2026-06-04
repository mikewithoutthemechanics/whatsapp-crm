'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import {
  getBrands,
  getBrand,
  createBrand,
  updateBrand,
  getUnits,
  createUnit,
  getLocations,
  createLocation,
  connectLocationWhatsapp,
  getPlatformSummary,
} from '../../lib/api';
import { Loader2, Plus, ExternalLink, ChevronDown, ChevronRight, Phone, MapPin, Users } from 'lucide-react';

type Brand = {
  id: string;
  name: string;
  tagline?: string;
  industry?: string;
  province?: string;
  city?: string;
  primary_color?: string;
  phone?: string;
  email?: string;
  website?: string;
  is_active: boolean;
  units?: unknown[];
  locations?: unknown[];
};

type Unit = { id: string; name: string; unit_type?: string; is_active: boolean };
type Location = { id: string; name: string; location_type?: string; province?: string; city?: string; whatsapp_connected: boolean; is_active: boolean };

export default function BusinessPage() {
  const router = useRouter();
  const [brands, setBrands] = useState<Brand[]>([]);
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});
  const [brandDetail, setBrandDetail] = useState<Record<string, Brand & { units: Unit[]; locations: Location[] }>>({});
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [creating, setCreating] = useState(false);

  const [newBrand, setNewBrand] = useState({
    name: '', tagline: '', industry: '', province: '', city: '',
    phone: '', email: '', website: '', primary_color: '#25D366',
  });

  useEffect(() => {
    if (!localStorage.getItem('wacrm_token')) return router.push('/');
    loadBrands();
  }, [router]);

  async function loadBrands() {
    setLoading(true);
    try {
      const res = await getBrands(true);
      setBrands(res.data || []);
    } catch (err: unknown) {
      if (err instanceof Error && (err.message.includes('401') || err.message.includes('403'))) {
        localStorage.removeItem('wacrm_token');
        router.push('/');
      }
    } finally {
      setLoading(false);
    }
  }

  async function toggleBrand(brandId: string) {
    const next = { ...expanded };
    if (next[brandId]) {
      delete next[brandId];
      setExpanded(next);
      return;
    }
    next[brandId] = true;
    setExpanded(next);
    if (!brandDetail[brandId]) {
      try {
        const detail = await getBrand(brandId);
        setBrandDetail((prev) => ({ ...prev, [brandId]: detail }));
      } catch { /* best-effort */ }
    }
  }

  async function handleCreateBrand() {
    if (!newBrand.name.trim()) return;
    setCreating(true);
    try {
      await createBrand({ ...newBrand, business_id: 'default' });
      setShowCreate(false);
      setNewBrand({ name: '', tagline: '', industry: '', province: '', city: '', phone: '', email: '', website: '', primary_color: '#25D366' });
      await loadBrands();
    } catch { /* handled */ }
    setCreating(false);
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-bold text-white">Theo Business Platform</h1>
          <p className="text-sm text-white/35 mt-0.5">Manage brands, units, locations, and WhatsApp sessions.</p>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold text-white cursor-pointer border-none transition-all"
          style={{ background: '#6366F1' }}
          onMouseEnter={(e) => ((e.target as HTMLButtonElement).style.background = '#4F46E5')}
          onMouseLeave={(e) => ((e.target as HTMLButtonElement).style.background = '#6366F1')}
        >
          <Plus size={15} /> New Brand
        </button>
      </div>

      {showCreate && (
        <div className="rounded-xl border p-5 space-y-4" style={{ background: '#151519', borderColor: 'rgba(255,255,255,0.06)' }}>
          <div className="flex items-center justify-between">
            <h2 className="text-base font-semibold text-white">Create TheoBrand</h2>
            <button
              onClick={() => setShowCreate(false)}
              className="text-white/40 hover:text-white cursor-pointer bg-transparent border-none text-xl"
            >×</button>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {[
              ['Brand Name', 'name', 'text'],
              ['Industry', 'industry', 'text'],
              ['Province', 'province', 'text'],
              ['City', 'city', 'text'],
              ['Phone', 'phone', 'tel'],
              ['Email', 'email', 'email'],
              ['Website', 'website', 'url'],
            ].map(([label, key, type]) => (
              <div key={key}>
                <label className="block text-[11px] text-white/35 uppercase mb-1">{label}</label>
                <input
                  type={type}
                  value={(newBrand as Record<string, string>)[key]}
                  onChange={(e) => setNewBrand({ ...newBrand, [key]: e.target.value })}
                  className="w-full px-3 py-2 rounded-lg text-sm text-white bg-white/[.04] border border-white/[.08] focus:border-indigo-500 outline-none placeholder:text-white/25"
                />
              </div>
            ))}
          </div>
          <div className="flex gap-2 pt-1">
            <button
              onClick={() => setShowCreate(false)}
              className="flex-1 py-2.5 rounded-lg text-sm text-white/55 cursor-pointer border border-white/[.08] bg-transparent font-medium hover:bg-white/[.04] transition-all"
            >
              Cancel
            </button>
            <button
              onClick={handleCreateBrand}
              disabled={creating || !newBrand.name.trim()}
              className="flex-1 py-2.5 rounded-lg text-sm font-semibold text-white cursor-pointer border-none transition-all"
              style={{ background: '#6366F1', opacity: (creating || !newBrand.name.trim()) ? 0.6 : 1 }}
            >
              {creating ? 'Creating…' : 'Create Brand'}
            </button>
          </div>
        </div>
      )}

      {loading ? (
        <div className="flex items-center justify-center h-64 text-white/30">
          <Loader2 className="animate-spin mr-2" /> Loading…
        </div>
      ) : brands.length === 0 ? (
        <div className="rounded-xl border p-12 text-center" style={{ background: 'rgba(255,255,255,0.02)', borderColor: 'rgba(255,255,255,0.06)' }}>
          <p className="text-white/25 text-sm">No TheoBrands yet. Click &quot;New Brand&quot; to create one.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {brands.map((brand) => {
            const isOpen = !!expanded[brand.id];
            const detail = brandDetail[brand.id];
            const units: Unit[] = (detail?.units || []) as Unit[];
            const locs: Location[] = (detail?.locations || []) as Location[];

            return (
              <div key={brand.id} className="rounded-xl border" style={{ background: 'rgba(255,255,255,0.02)', borderColor: 'rgba(255,255,255,0.06)' }}>
                <button
                  onClick={() => toggleBrand(brand.id)}
                  className="w-full flex items-center justify-between px-5 py-4 cursor-pointer bg-transparent border-none text-left"
                >
                  <div className="flex items-center gap-3">
                    {isOpen ? <ChevronDown size={14} className="text-white/40" /> : <ChevronRight size={14} className="text-white/40" />}
                    <div>
                      <p className="text-white font-medium text-sm">{brand.name}</p>
                      <p className="text-[11px] text-white/35 mt-0.5">
                        {brand.industry || '—'} · {brand.city || brand.province || '—'} · {brand.phone || '—'}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-[11px] text-white/25">{units.length} units · {locs.length} locs</span>
                    {brand.website && (
                      <a
                        href={brand.website}
                        target="_blank"
                        rel="noopener noreferrer"
                        onClick={(e) => e.stopPropagation()}
                        className="text-white/30 hover:text-white no-underline"
                      >
                        <ExternalLink size={13} />
                      </a>
                    )}
                  </div>
                </button>

                {isOpen && (
                  <div className="px-5 pb-5 border-t border-white/[.04] space-y-4">
                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 pt-4">
                      <div>
                        <label className="block text-[11px] text-white/35 uppercase mb-1">Brand Name</label>
                        <input
                          defaultValue={brand.name}
                          onBlur={async (e) => {
                            if (e.target.value !== brand.name) {
                              await updateBrand(brand.id, { name: e.target.value });
                              await loadBrands();
                            }
                          }}
                          className="w-full px-3 py-2 rounded-lg text-sm text-white bg-white/[.04] border border-white/[.08] outline-none"
                        />
                      </div>
                      <div>
                        <label className="block text-[11px] text-white/35 uppercase mb-1">Tagline</label>
                        <input
                          defaultValue={brand.tagline || ''}
                          onBlur={async (e) => {
                            await updateBrand(brand.id, { tagline: e.target.value });
                            await loadBrands();
                          }}
                          className="w-full px-3 py-2 rounded-lg text-sm text-white bg-white/[.04] border border-white/[.08] outline-none"
                        />
                      </div>
                      <div>
                        <label className="block text-[11px] text-white/35 uppercase mb-1">Industry</label>
                        <input
                          defaultValue={brand.industry || ''}
                          onBlur={async (e) => {
                            await updateBrand(brand.id, { industry: e.target.value });
                            await loadBrands();
                          }}
                          className="w-full px-3 py-2 rounded-lg text-sm text-white bg-white/[.04] border border-white/[.08] outline-none"
                        />
                      </div>
                      <div>
                        <label className="block text-[11px] text-white/35 uppercase mb-1">Primary Color</label>
                        <div className="flex gap-2">
                          <input
                            type="color"
                            defaultValue={brand.primary_color || '#25D366'}
                            onChange={async (e) => {
                              await updateBrand(brand.id, { primary_color: e.target.value });
                              await loadBrands();
                            }}
                            className="w-10 h-9 rounded border border-white/[.08] bg-transparent cursor-pointer"
                          />
                          <input
                            defaultValue={brand.primary_color || '#25D366'}
                            className="flex-1 px-3 py-2 rounded-lg text-sm text-white bg-white/[.04] border border-white/[.08] outline-none font-mono"
                          />
                        </div>
                      </div>
                    </div>

                    {/* Units */}
                    <UnitSection
                      brandId={brand.id}
                      units={units}
                      onReload={loadBrands}
                    />

                    {/* Locations */}
                    <LocationSection
                      brandId={brand.id}
                      locations={locs}
                      onReload={loadBrands}
                    />
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

function UnitSection({ brandId, units, onReload }: { brandId: string; units: Unit[]; onReload: () => void }) {
  const [showAdd, setShowAdd] = useState(false);
  const [name, setName] = useState('');
  const [unitType, setUnitType] = useState('');

  return (
    <div className="pt-4 border-t border-white/[.04]">
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-xs font-semibold text-white/60 uppercase tracking-wider flex items-center gap-1.5">
          <Users size={12} /> Business Units
        </h3>
        <button
          onClick={() => setShowAdd(true)}
          className="flex items-center gap-1 text-[11px] text-indigo-400 cursor-pointer bg-transparent border border-indigo-500/20 px-2 py-1 rounded hover:bg-indigo-500/10 transition-colors"
        >
          <Plus size={12} /> Add Unit
        </button>
      </div>
      {showAdd && (
        <div className="flex gap-2 mb-2">
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Unit name"
            className="px-3 py-1.5 rounded text-sm text-white bg-white/[.04] border border-white/[.08] outline-none flex-1"
          />
          <input
            value={unitType}
            onChange={(e) => setUnitType(e.target.value)}
            placeholder="Type"
            className="px-3 py-1.5 rounded text-sm text-white bg-white/[.04] border border-white/[.08] outline-none w-32"
          />
          <button
            onClick={async () => {
              if (!name.trim()) return;
              await createUnit(brandId, { name, unit_type: unitType, business_id: 'default' });
              setName('');
              setUnitType('');
              setShowAdd(false);
              onReload();
            }}
            className="px-3 py-1.5 rounded text-sm text-white cursor-pointer border-none"
            style={{ background: '#10B981' }}
          >
            Save
          </button>
        </div>
      )}
      {units.length === 0 ? (
        <p className="text-xs text-white/20">No units configured.</p>
      ) : (
        <div className="flex flex-wrap gap-2">
          {units.map((u) => (
            <span key={u.id} className="text-xs px-2.5 py-1.5 rounded-full bg-white/[.05] text-white/60 border border-white/[.06]">
              {u.name} {u.unit_type ? `· ${u.unit_type}` : ''}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

function LocationSection({ brandId, locations, onReload }: { brandId: string; locations: Location[]; onReload: () => void }) {
  const [showAdd, setShowAdd] = useState(false);
  const [name, setName] = useState('');
  const [locType, setLocType] = useState('');
  const [city, setCity] = useState('');
  const [province, setProvince] = useState('');

  return (
    <div className="pt-4 border-t border-white/[.04]">
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-xs font-semibold text-white/60 uppercase tracking-wider flex items-center gap-1.5">
          <MapPin size={12} /> Locations
        </h3>
        <button
          onClick={() => setShowAdd(true)}
          className="flex items-center gap-1 text-[11px] text-emerald-400 cursor-pointer bg-transparent border border-emerald-500/20 px-2 py-1 rounded hover:bg-emerald-500/10 transition-colors"
        >
          <Plus size={12} /> Add Location
        </button>
      </div>
      {showAdd && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 mb-2">
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Location name"
            className="px-3 py-1.5 rounded text-sm text-white bg-white/[.04] border border-white/[.08] outline-none"
          />
          <input
            value={locType}
            onChange={(e) => setLocType(e.target.value)}
            placeholder="Type (store, office, depot)"
            className="px-3 py-1.5 rounded text-sm text-white bg-white/[.04] border border-white/[.08] outline-none"
          />
          <input
            value={city}
            onChange={(e) => setCity(e.target.value)}
            placeholder="City"
            className="px-3 py-1.5 rounded text-sm text-white bg-white/[.04] border border-white/[.08] outline-none"
          />
          <input
            value={province}
            onChange={(e) => setProvince(e.target.value)}
            placeholder="Province"
            className="px-3 py-1.5 rounded text-sm text-white bg-white/[.04] border border-white/[.08] outline-none"
          />
          <button
            onClick={async () => {
              if (!name.trim()) return;
              await createLocation(brandId, { name, location_type: locType, city, province, business_id: 'default' });
              setName('');
              setLocType('');
              setCity('');
              setProvince('');
              setShowAdd(false);
              onReload();
            }}
            className="px-3 py-1.5 rounded text-sm text-white cursor-pointer border-none"
            style={{ background: '#10B981' }}
          >
            Save
          </button>
        </div>
      )}
      {locations.length === 0 ? (
        <p className="text-xs text-white/20">No locations yet. Add your first store, depot, or office.</p>
      ) : (
        <div className="space-y-1.5">
          {locations.map((loc) => (
            <div
              key={loc.id}
              className="flex items-center justify-between px-3 py-2 rounded-lg"
              style={{ background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.04)' }}
            >
              <div className="flex items-center gap-2">
                <MapPin size={12} className="text-white/25" />
                <span className="text-xs text-white/70 font-medium">{loc.name}</span>
                {loc.location_type && <span className="text-[10px] text-white/30">· {loc.location_type}</span>}
                {loc.city && <span className="text-[10px] text-white/25">· {loc.city}, {loc.province}</span>}
              </div>
              <div className="flex items-center gap-2">
                {loc.whatsapp_connected ? (
                  <span className="text-[10px] text-emerald-400 flex items-center gap-1">
                    <Phone size={10} /> {loc.whatsapp_number}
                  </span>
                ) : (
                  <span className="text-[10px] text-white/20">No WhatsApp</span>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
