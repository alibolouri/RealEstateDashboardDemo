import type { ListingCard as ListingCardType } from "../lib/api";

type Props = {
  listing: ListingCardType;
  compact?: boolean;
};

function formatPrice(listing: ListingCardType) {
  return listing.listing_type === "short_stay" ? `$${listing.price}/night` : `$${listing.price.toLocaleString()}`;
}

export function ListingCard({ listing, compact = false }: Props) {
  return (
    <article className="listing-card">
      <div className="listing-card__header">
        <div>
          <div className="listing-card__title">{listing.title}</div>
          <div className="listing-card__location">{listing.city}, {listing.state}</div>
          {!compact ? <div className="listing-card__address">{listing.address}</div> : null}
        </div>
        <span className="micro-pill">{listing.status}</span>
      </div>

      <div className="listing-card__stats">
        <strong className="listing-card__price">{formatPrice(listing)}</strong>
        <span>{listing.bedrooms} bd</span>
        <span>{listing.bathrooms} ba</span>
        {listing.square_feet ? <span>{listing.square_feet.toLocaleString()} sq ft</span> : null}
      </div>

      {!compact ? <div className="listing-card__description">{listing.short_description}</div> : null}

      <div className="listing-card__footer">
        <span className="micro-pill">{listing.data_status}</span>
        <span className="u-tertiary">{listing.source}</span>
      </div>
    </article>
  );
}
