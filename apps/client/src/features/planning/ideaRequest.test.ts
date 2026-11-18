import { fromParams, ideaQuery, toParams, type IdeaRequest } from './ideaRequest';

const base: IdeaRequest = { mood: 'kitchen', q: '', lean: null, maxMinutes: null, serves: null };

describe('toParams / fromParams', () => {
  it('round-trips a setup through the route params', () => {
    const picked: IdeaRequest = {
      mood: 'specific',
      q: 'chicken',
      lean: 'vegetarian',
      maxMinutes: 45,
      serves: 2,
    };
    expect(fromParams(toParams(picked))).toEqual(picked);
  });

  it('reads nothing (Just tonight from Home) as Use my Kitchen, no limits', () => {
    expect(fromParams({})).toEqual(base);
  });

  it('ignores junk in a link', () => {
    expect(fromParams({ mood: 'evil', serves: '-3', max: 'soon', lean: 'x' })).toEqual(base);
  });

  it('a specific mood with no words falls back to the Kitchen', () => {
    expect(fromParams({ mood: 'specific', q: '  ' }).mood).toBe('kitchen');
  });
});

describe('ideaQuery', () => {
  it('sends the mood, words and lean', () => {
    expect(ideaQuery({ ...base, mood: 'specific', q: 'pasta', lean: 'vegetarian' }, 'all')).toEqual(
      { mood: 'specific', q: 'pasta', vegetarian: true },
    );
  });

  it('takes the tighter time limit of Ready in and the Quick chip', () => {
    expect(ideaQuery({ ...base, maxMinutes: 45 }, 'quick')).toEqual({
      mood: 'kitchen',
      max_minutes: 30,
    });
    expect(ideaQuery({ ...base, maxMinutes: 20 }, 'quick').max_minutes).toBe(20);
    expect(ideaQuery({ ...base, lean: 'quick' }, 'all').max_minutes).toBe(30);
  });

  it('Use my Kitchen chip means nothing to buy; the Vegetarian chip filters too', () => {
    expect(ideaQuery(base, 'kitchen')).toEqual({ mood: 'kitchen', nothing_to_buy: true });
    expect(ideaQuery(base, 'vegetarian')).toEqual({ mood: 'kitchen', vegetarian: true });
  });

  it('healthy is asked of Sweep, so it adds no filter', () => {
    expect(ideaQuery({ ...base, lean: 'healthy' }, 'all')).toEqual({ mood: 'kitchen' });
  });
});
